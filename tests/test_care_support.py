import pytest

from care_support import (
    build_search_query,
    calculate_distance_km,
    city_hint,
    embed_map_url,
    normalize_place,
    sort_results_by_distance,
)


def test_build_search_query_uses_city_and_specialty():
    assert build_search_query("New York", "psychologist") == "psychologist in New York"


def test_build_search_query_defaults_to_healthcare_terms_when_empty_specialty():
    assert build_search_query("Seattle", "") == "doctor clinic hospital psychiatrist psychologist in Seattle"


def test_build_search_query_trims_whitespace():
    assert build_search_query("  Bengaluru  ", "  psychiatrist  ") == "psychiatrist in Bengaluru"


def test_normalize_place_extracts_key_fields():
    item = {
        "name": "Mindful Care Clinic",
        "display_name": "Mindful Care Clinic, New York, USA",
        "lat": "40.7128",
        "lon": "-74.0060",
        "type": "clinic",
        "class": "amenity",
        "address": {"city": "New York", "state": "New York", "country": "USA"},
        "phone": "+1-555-1234",
        "website": "https://example.com",
    }

    normalized = normalize_place(item)

    assert normalized["title"] == "Mindful Care Clinic"
    assert normalized["city"] == "New York"
    assert normalized["state"] == "New York"
    assert normalized["country"] == "USA"
    assert normalized["phone"] == "+1-555-1234"
    assert normalized["website"] == "https://example.com"


def test_normalize_place_handles_missing_optional_fields():
    item = {
        "display_name": "Care Center, Berlin, Germany",
        "lat": "52.52",
        "lon": "13.405",
    }

    normalized = normalize_place(item)

    assert normalized["title"] == "Care Center"
    assert normalized["city"] == "Berlin"
    assert normalized["phone"] == ""
    assert normalized["website"] == ""


def test_city_hint_returns_second_last_segment_when_available():
    assert city_hint("Mindful Care Clinic, New York, USA") == "New York"


def test_embed_map_url_contains_expected_coordinates():
    result = embed_map_url("12.9716", "77.5946")

    assert "openstreetmap.org/export/embed.html" in result
    assert "12.9716" in result
    assert "77.5946" in result


def test_calculate_distance_km_is_reasonable_for_same_point():
    assert calculate_distance_km(12.9716, 77.5946, 12.9716, 77.5946) == pytest.approx(0.0)


def test_sort_results_by_distance_sorts_nearest_first():
    places = [
        {"title": "Far Place", "lat": "12.9800", "lon": "77.6000"},
        {"title": "Near Place", "lat": "12.9716", "lon": "77.5946"},
    ]

    sorted_places = sort_results_by_distance(places, 12.9716, 77.5946)

    assert sorted_places[0]["title"] == "Near Place"
    assert sorted_places[1]["title"] == "Far Place"


def test_build_search_query_rejects_missing_city():
    with pytest.raises(ValueError):
        build_search_query("", "psychologist")
