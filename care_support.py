from __future__ import annotations

import os
from math import atan2, cos, radians, sin, sqrt
from typing import Any

import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GOOGLE_PLACES_BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DEFAULT_USER_AGENT = "Nova-AI-Habit-Addiction-Coach"


def build_search_query(city: str, specialty: str) -> str:
    """Build a query string for the public Nominatim search API."""
    city = (city or "").strip()
    specialty = (specialty or "").strip()
    if not city:
        raise ValueError("A city is required for nearby care lookup.")
    if not specialty:
        specialty = "doctor clinic hospital psychiatrist psychologist"
    return f"{specialty} in {city}"


def build_overpass_query(lat: float, lon: float, radius_km: int, specialty: str) -> str:
    """Build an Overpass query that targets likely care-related OSM amenities around a point."""
    radius_m = max(5000, int(radius_km * 1000))
    specialty = (specialty or "").strip().lower()

    tag_pairs: list[tuple[str, str]] = [
        ("amenity", "clinic"),
        ("amenity", "hospital"),
    ]

    if specialty in {"psychologist", "psychiatrist", "therapist"}:
        tag_pairs.extend([
            ("healthcare", "psychotherapist"),
            ("healthcare", "psychiatrist"),
        ])
    elif specialty in {"doctor", "clinic", "hospital"}:
        tag_pairs = [
            ("amenity", "clinic"),
            ("amenity", "hospital"),
            ("healthcare", "doctor"),
        ]

    unique_pairs: list[tuple[str, str]] = []
    for pair in tag_pairs:
        if pair not in unique_pairs:
            unique_pairs.append(pair)

    selectors = "\n".join(
        f'  node["{key}"="{value}"](around:{radius_m},{lat},{lon});'
        for key, value in unique_pairs
    )

    return f"""
[out:json][timeout:25];
(
{selectors}
);
out center 40;
""".strip()


def build_google_places_url(lat: float, lon: float, radius_m: int, keyword: str) -> str:
    """Build a Google Places nearby-search URL using the configured API key when available."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY") or "DEMO_API_KEY"

    keyword = (keyword or "clinic").strip()
    params = {
        "location": f"{lat},{lon}",
        "radius": str(max(1000, int(radius_m))),
        "keyword": keyword,
        "key": api_key,
    }
    return f"{GOOGLE_PLACES_BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())


def normalize_place(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Nominatim result into a lightweight, UI-friendly dict."""
    address = item.get("address") or {}
    display_name = (item.get("display_name") or "").strip()
    title = (item.get("name") or display_name.split(",")[0] or "Healthcare provider").strip()

    return {
        "title": title,
        "display_name": display_name,
        "lat": item.get("lat"),
        "lon": item.get("lon"),
        "type": item.get("type") or "healthcare",
        "category": item.get("class") or "amenity",
        "city": address.get("city") or address.get("town") or address.get("village") or city_hint(display_name),
        "state": address.get("state") or "",
        "country": address.get("country") or "",
        "phone": item.get("phone") or "",
        "website": item.get("website") or "",
    }


def city_hint(display_name: str) -> str:
    parts = [part.strip() for part in display_name.split(",") if part.strip()]
    return parts[-2] if len(parts) >= 2 else ""


def geocode_place(query: str) -> tuple[float, float]:
    """Resolve a city or place name to lat/lon using Nominatim."""
    query = (query or "").strip()
    if not query:
        raise ValueError("A city is required for nearby care lookup.")

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params=params,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=12,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload:
        raise ValueError(f"No geographic coordinates found for: {query}")

    return float(payload[0]["lat"]), float(payload[0]["lon"])


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance in kilometers between two lat/lon points using the haversine formula."""
    radius = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def sort_results_by_distance(places: list[dict[str, Any]], center_lat: float, center_lon: float) -> list[dict[str, Any]]:
    """Add distance metadata and sort care results from nearest to farthest."""
    enriched: list[dict[str, Any]] = []
    for place in places:
        try:
            lat = float(place.get("lat"))
            lon = float(place.get("lon"))
            distance = calculate_distance_km(center_lat, center_lon, lat, lon)
        except (TypeError, ValueError):
            distance = float("inf")

        item = dict(place)
        item["distance_km"] = round(distance, 2) if distance != float("inf") else None
        enriched.append(item)

    enriched.sort(key=lambda item: item.get("distance_km") if item.get("distance_km") is not None else float("inf"))
    return enriched


def search_nearby_care(
    city: str,
    specialty: str = "psychologist doctor clinic hospital",
    radius_km: int = 25,
    limit: int = 6,
    center_lat: float | None = None,
    center_lon: float | None = None,
) -> list[dict[str, Any]]:
    """Query Google Places first when configured, then fall back to public OpenStreetMap sources."""
    if center_lat is None or center_lon is None:
        center_lat, center_lon = geocode_place(city)

    google_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    normalized: list[dict[str, Any]] = []

    if google_key:
        try:
            places_url = build_google_places_url(center_lat, center_lon, radius_km * 1000, specialty)
            places_response = requests.get(places_url, timeout=15)
            places_response.raise_for_status()
            payload = places_response.json()
            for item in payload.get("results", [])[:limit]:
                geometry = item.get("geometry") or {}
                loc = geometry.get("location") or {}
                normalized.append({
                    "title": item.get("name") or "Healthcare provider",
                    "display_name": item.get("vicinity") or item.get("name") or "Healthcare provider",
                    "lat": loc.get("lat"),
                    "lon": loc.get("lng"),
                    "type": item.get("types", ["healthcare"])[0] if item.get("types") else "healthcare",
                    "category": "place",
                    "city": city,
                    "state": "",
                    "country": "",
                    "phone": item.get("formatted_phone_number") or "",
                    "website": item.get("website") or "",
                })
        except Exception:
            normalized = []

    if not normalized:
        overpass_query = build_overpass_query(center_lat, center_lon, radius_km, specialty)
        overpass_payload = {"data": overpass_query}

        overpass_response = requests.post(
            OVERPASS_URL,
            data=overpass_payload,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=20,
        )
        overpass_response.raise_for_status()

        payload = overpass_response.json()
        elements = payload.get("elements") or []
        for item in elements:
            tags = item.get("tags") or {}
            display_name = tags.get("name") or tags.get("operator") or "Healthcare provider"
            normalized.append({
                "title": display_name,
                "display_name": display_name,
                "lat": item.get("lat") or item.get("center", {}).get("lat"),
                "lon": item.get("lon") or item.get("center", {}).get("lon"),
                "type": tags.get("amenity") or tags.get("healthcare") or "healthcare",
                "category": "amenity",
                "city": tags.get("city") or tags.get("town") or tags.get("village") or city,
                "state": tags.get("state") or tags.get("province") or "",
                "country": tags.get("country") or "",
                "phone": tags.get("phone") or "",
                "website": tags.get("website") or "",
            })

    if not normalized:
        fallback_query = build_search_query(city=city, specialty=specialty)
        fallback_params = {
            "q": fallback_query,
            "format": "jsonv2",
            "limit": str(max(1, min(limit, 10))),
            "addressdetails": "1",
        }
        fallback_response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=fallback_params,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=12,
        )
        fallback_response.raise_for_status()
        normalized = [normalize_place(item) for item in fallback_response.json()]

    sorted_results = sort_results_by_distance(normalized, center_lat, center_lon)
    filtered = [item for item in sorted_results if item.get("distance_km") is not None and item.get("distance_km") <= radius_km]
    if filtered:
        return filtered[:limit]
    return sorted_results[:limit]


def embed_map_url(lat: str, lon: str) -> str:
    """Return a public OpenStreetMap embed URL centered on a location."""
    return f"https://www.openstreetmap.org/export/embed.html?bbox={float(lon)-0.01}%2C{float(lat)-0.01}%2C{float(lon)+0.01}%2C{float(lat)+0.01}&layer=mapnik&marker={lat}%2C{lon}"
