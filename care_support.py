from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Any

import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
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
    """Query the public Nominatim API for healthcare providers near a city and sort them by distance."""
    query = build_search_query(city=city, specialty=specialty)
    if center_lat is None or center_lon is None:
        center_lat, center_lon = geocode_place(city)

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": str(max(1, min(limit, 10))),
        "addressdetails": "1",
    }

    response = requests.get(
        NOMINATIM_SEARCH_URL,
        params=params,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=12,
    )
    response.raise_for_status()

    payload = response.json()
    normalized = [normalize_place(item) for item in payload]
    sorted_results = sort_results_by_distance(normalized, center_lat, center_lon)

    filtered = [item for item in sorted_results if item.get("distance_km") is not None and item.get("distance_km") <= radius_km]
    if filtered:
        return filtered[:limit]
    return sorted_results[:limit]


def embed_map_url(lat: str, lon: str) -> str:
    """Return a public OpenStreetMap embed URL centered on a location."""
    return f"https://www.openstreetmap.org/export/embed.html?bbox={float(lon)-0.01}%2C{float(lat)-0.01}%2C{float(lon)+0.01}%2C{float(lat)+0.01}&layer=mapnik&marker={lat}%2C{lon}"
