"""
Tests for the farmer data world: its isolation from the trader stores, its
place registry, and the rule that a sell/hold call is only ever issued for a
crop and district whose record earned one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mandisense_ai.farmer import dashboard, registry, world
from mandisense_ai.forecasting import config as forecast_config


def test_farmer_stores_are_separate_from_the_trader_stores():
    """Republishing farmer forecasts must not be able to move a trader number,
    and a farmer must never read the shared store's synthetic Karnataka rows."""
    trader = {forecast_config.observations_path(), forecast_config.forecast_store_path(),
              forecast_config.model_registry_dir(), forecast_config.ledger_path()}
    farmer = {world.DISTRICT_OBSERVATIONS, world.MANDI_PRICES, world.FORECAST_STORE, world.BUNDLE_DIR, world.LEDGER}
    assert not trader & farmer
    assert "farmer" in Path(world.FORECAST_STORE).parts


def test_a_district_id_is_not_turned_into_a_trader_mandi_id():
    # canonical_market("kolar") is "kolar_apmc" -- a different series entirely.
    assert registry.resolve_place(" Kolar ") == "kolar"
    assert registry.series_place("kolar_apmc") == "kolar"
    assert registry.series_place("kolar") == "kolar"
    assert registry.series_place("unknown_place") == "unknown_place"


def test_every_mandi_belongs_to_a_known_district_and_has_three_names():
    for mandi in registry.MANDIS.values():
        assert mandi.district in registry.DISTRICTS
        assert mandi.name and mandi.name_kn and mandi.name_hi
        assert registry.display_name(mandi.id, "kn") == mandi.name_kn


def test_nearest_district_from_a_point_in_kolar():
    district, km = registry.nearest_district(13.14, 78.13)
    assert district.id == "kolar"
    assert km < 5


def _forecast(decision="HOLD", p_decline=0.3, change=4.0):
    return [{"horizon": 5, "date": "2026-10-03", "price": 1500.0, "p05": 1200.0, "p25": 1400.0, "p75": 1600.0,
             "p95": 1800.0, "change_pct": change, "decision": decision, "p_decline": p_decline}]


def test_no_call_is_issued_for_a_series_that_has_not_earned_one():
    call = dashboard._call("garlic", "bengaluru", _forecast(), {"serves_call": False})
    assert call["type"] == "RANGE_ONLY"
    assert "decision" not in call


def test_a_series_that_earned_a_call_gets_it_with_a_calibrated_confidence():
    hold = dashboard._call("potato", "kolar", _forecast("HOLD", p_decline=0.3), {"serves_call": True})
    assert (hold["type"], hold["decision"]) == ("ADVISED", "HOLD")
    assert hold["confidence"] == pytest.approx(0.7)
    sell = dashboard._call("potato", "kolar", _forecast("SELL", p_decline=0.8, change=-3.0), {"serves_call": True})
    assert (sell["decision"], sell["confidence"]) == ("SELL", pytest.approx(0.8))


def test_an_abstaining_policy_is_reported_as_abstained_not_as_advice():
    call = dashboard._call("potato", "kolar", _forecast("WAIT", p_decline=0.5, change=0.2), {"serves_call": True})
    assert call["type"] == "ABSTAINED"


def test_no_forecast_at_all_is_none():
    assert dashboard._call("potato", "kolar", [], {"serves_call": True})["type"] == "NONE"


def test_ask_reads_the_crop_and_place_in_three_languages():
    assert dashboard.ask("kolar tomato price")["crop"] == "tomato"
    assert dashboard.ask("kolar tomato price")["district"] == "kolar"
    assert dashboard.ask("ಕೋಲಾರ ಈರುಳ್ಳಿ ಬೆಲೆ") == {"crop": "onion", "district": "kolar", "understood": True}
    assert dashboard.ask("चिक्कबल्लापुर में आलू")["crop"] == "potato"
    assert dashboard.ask("what is the weather")["understood"] is False


def test_ask_uses_the_default_place_when_none_is_named():
    assert dashboard.ask("ginger", "bengaluru")["district"] == "bengaluru"


# ── the significance rule behind the earned call ────────────────────────────


def test_holm_adjustment_is_monotone_and_capped():
    from mandisense_ai.farmer.significance import holm

    adjusted = holm([0.001, 0.04, 0.5, 0.9])
    assert list(adjusted) == pytest.approx([0.004, 0.12, 1.0, 1.0])
    assert all(0 <= a <= 1 for a in adjusted)


def test_dm_test_calls_a_clearly_better_model_better_and_a_tie_a_tie():
    import numpy as np

    from mandisense_ai.farmer.significance import dm_test

    rng = np.random.default_rng(0)
    dates = np.repeat(np.arange(300), 2)
    baseline = rng.uniform(0.04, 0.06, 600)
    stat, p, n = dm_test(baseline, baseline - 0.01, dates, 5)
    assert stat > 0 and p < 0.001 and n == 300
    stat, p, _ = dm_test(baseline, baseline + rng.normal(0, 1e-4, 600), dates, 5)
    assert p > 0.05


def test_several_series_on_one_date_count_once_not_several_times():
    """Averaging over dates first: duplicating every series must not make the
    evidence look stronger."""
    import numpy as np

    from mandisense_ai.farmer.significance import dm_test

    rng = np.random.default_rng(1)
    dates = np.arange(200)
    base = rng.uniform(0.03, 0.07, 200)
    gain = rng.normal(0.002, 0.02, 200)
    _, p_once, _ = dm_test(base, base - gain, dates, 3)
    _, p_twice, _ = dm_test(np.tile(base, 5), np.tile(base - gain, 5), np.tile(dates, 5), 3)
    assert p_once == pytest.approx(p_twice, rel=1e-6)
