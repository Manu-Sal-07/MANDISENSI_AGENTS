"""The farmer must be told when the advice is for a day that has already passed.

The decision day is always the day after the newest panel date, so comparing it with that date (the old check) never fired:
advice built from data ending 11 Nov said "sell today (12 Nov)" on 14 Nov with no warning.
"""

from datetime import date

import pandas as pd

from mandisense_ai.market_choice import service


def _ev(as_of: str):
    as_of_ts = pd.Timestamp(as_of)
    return {"as_of": as_of_ts, "decision_day": as_of_ts + pd.Timedelta(days=1)}


def test_advice_for_a_past_day_is_flagged_stale(monkeypatch):
    monkeypatch.setattr(service, "_today_in_india", lambda: date(2026, 11, 14))
    assert "stale_data" in service._caveats({}, {"kind": "mandi", "chance_open": 0.9}, _ev("2026-11-11"))


def test_advice_for_today_is_not_flagged(monkeypatch):
    monkeypatch.setattr(service, "_today_in_india", lambda: date(2026, 11, 12))
    assert "stale_data" not in service._caveats({}, {"kind": "mandi", "chance_open": 0.9}, _ev("2026-11-11"))


def test_stale_headline_does_not_say_today():
    from mandisense_ai.intelligence.explain import explain

    rec = {"crop": "tomato", "caveats": ["stale_data"], "confidence_pct": 90, "alpha": 0.1, "quantity_quintals": 20, "decision_day": "2026-11-12",
           "origin": {"lat": 13.1, "lon": 78.1},
           "recommended": {"kind": "mandi", "mandi_name": "Ramanagara", "mandi_name_kn": "ರಾಮನಗರ", "mandi_name_hi": "रामनगर", "sale_date": "2026-11-12",
                           "hold_days": 0, "expected_net_per_q": 1762, "floor_per_q": 1225, "chance_open": 0.97, "distance_km": 50.0}}
    for lang, today in (("en", "today"), ("kn", "ಇಂದು"), ("hi", "आज")):
        out = explain(rec, None, lang, use_llm=False)
        assert today not in out["headline"], out["headline"]
