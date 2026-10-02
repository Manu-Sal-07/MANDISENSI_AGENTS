"""Tests for shared farmer-feature reference data (mandi coordinates, shelf life)."""

from __future__ import annotations

import pytest

from mandisense_ai.farmer.reference import (
    MANDI_COORDINATES,
    MANDI_DISPLAY_NAMES,
    distance_between_mandis_km,
    haversine_km,
    nearest_mandis,
    shelf_profile,
)


def test_every_mandi_has_a_display_name():
    for mandi_id in MANDI_COORDINATES:
        assert mandi_id in MANDI_DISPLAY_NAMES
        assert MANDI_DISPLAY_NAMES[mandi_id]


def test_distance_to_self_is_zero():
    assert haversine_km((13.0, 77.5), (13.0, 77.5)) == pytest.approx(0.0, abs=1e-6)


def test_distance_is_symmetric():
    a, b = (13.0270, 77.5540), (13.1372, 78.1298)
    assert haversine_km(a, b) == pytest.approx(haversine_km(b, a))


def test_known_mandi_pair_distance_is_plausible():
    """Bangalore Yeshwanthpur to Kolar is roughly 65-75km by road; straight-line
    should be in a sane neighbourhood of that, not off by an order of magnitude."""
    km = distance_between_mandis_km("bangalore_yeshwanthpur", "kolar_apmc")
    assert km is not None
    assert 40 < km < 90


def test_unknown_mandi_pair_returns_none():
    assert distance_between_mandis_km("bangalore_yeshwanthpur", "not_a_real_mandi") is None


def test_nearest_mandis_are_sorted_ascending_by_distance():
    lat, lon = MANDI_COORDINATES["kolar_apmc"]
    result = nearest_mandis(lat, lon, limit=5)
    distances = [r["distance_km"] for r in result]
    assert distances == sorted(distances)
    # The origin's own mandi should be nearest (distance ~0).
    assert result[0]["mandi_id"] == "kolar_apmc"
    assert result[0]["distance_km"] == pytest.approx(0.0, abs=0.1)


def test_nearest_mandis_respects_limit():
    result = nearest_mandis(13.0, 77.5, limit=3)
    assert len(result) == 3


def test_shelf_profile_distinguishes_perishable_from_storable():
    tomato = shelf_profile("tomato")
    onion = shelf_profile("onion")
    assert tomato.shelf_life_days < onion.shelf_life_days
    assert tomato.daily_loss_pct > onion.daily_loss_pct


def test_unknown_crop_gets_a_conservative_default_not_a_crash():
    profile = shelf_profile("dragonfruit")
    assert profile.shelf_life_days > 0
    assert profile.category == "unknown"
