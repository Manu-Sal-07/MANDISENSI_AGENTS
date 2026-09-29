"""
Tests for price alerts and the village truck-sharing board.

Both are file-backed, low-volume stores (see their module docstrings for
why); the properties that matter are the same ones any small persisted
store needs: writes are idempotent/isolated per test, invalid input is
rejected before it is written, and capacity/ownership rules cannot be
bypassed by a malformed request.
"""

from __future__ import annotations

import pytest

from mandisense_ai.farmer import alerts, truck_share


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "_alerts_path", lambda: tmp_path / "alerts.json")
    monkeypatch.setattr(alerts, "_outbox_path", lambda: tmp_path / "outbox.jsonl")
    monkeypatch.setattr(truck_share, "_board_path", lambda: tmp_path / "board.json")


# ── alerts ──────────────────────────────────────────────────────────────────


def test_create_and_list_alert_round_trips():
    created = alerts.create_alert("9900011122", "tomato", "kolar_apmc", "PRICE_ABOVE", 2000.0)
    assert created["status"] == "OK"
    listed = alerts.list_alerts("9900011122")
    assert len(listed) == 1
    assert listed[0]["commodity"] == "tomato"


def test_invalid_alert_type_is_rejected():
    result = alerts.create_alert("9900011122", "tomato", "kolar_apmc", "NONSENSE")
    assert result["status"] == "ERROR"
    assert alerts.list_alerts("9900011122") == []


def test_threshold_alert_without_a_threshold_is_rejected():
    result = alerts.create_alert("9900011122", "tomato", "kolar_apmc", "PRICE_ABOVE", threshold=None)
    assert result["status"] == "ERROR"


def test_decision_alert_needs_no_threshold():
    result = alerts.create_alert("9900011122", "tomato", "kolar_apmc", "DECISION_SELL")
    assert result["status"] == "OK"


def test_alerts_are_scoped_to_their_own_phone_number():
    alerts.create_alert("9900011122", "tomato", "kolar_apmc", "DECISION_SELL")
    alerts.create_alert("9900033344", "onion", "kolar_apmc", "DECISION_SELL")
    assert len(alerts.list_alerts("9900011122")) == 1
    assert len(alerts.list_alerts("9900033344")) == 1


def test_delete_alert_removes_only_that_phones_alert():
    created = alerts.create_alert("9900011122", "tomato", "kolar_apmc", "DECISION_SELL")
    alert_id = created["alert"]["id"]

    # A different phone cannot delete someone else's alert.
    denied = alerts.delete_alert("9900099999", alert_id)
    assert denied["status"] == "ERROR"
    assert len(alerts.list_alerts("9900011122")) == 1

    ok = alerts.delete_alert("9900011122", alert_id)
    assert ok["status"] == "OK"
    assert alerts.list_alerts("9900011122") == []


def test_evaluate_alerts_never_raises_when_forecast_service_is_unavailable(monkeypatch):
    alerts.create_alert("9900011122", "tomato", "kolar_apmc", "PRICE_ABOVE", 100.0)

    class _Unavailable:
        is_available = False

    monkeypatch.setattr(
        "mandisense_ai.forecasting.service.get_forecast_service", lambda: _Unavailable()
    )
    result = alerts.evaluate_alerts()
    assert result["checked"] == 1
    assert result["triggered"] == 0


def test_evaluate_alerts_triggers_on_a_crossed_threshold(monkeypatch):
    alerts.create_alert("9900011122", "tomato", "kolar_apmc", "PRICE_ABOVE", 1900.0)

    class _Service:
        is_available = True

        def get_curve(self, commodity, mandi_id):
            return [{"horizon_days": 1, "status": "OK", "forecast_price": 2100.0, "decision": "HOLD"}]

    monkeypatch.setattr("mandisense_ai.forecasting.service.get_forecast_service", lambda: _Service())
    result = alerts.evaluate_alerts()
    assert result["triggered"] == 1

    outbox = (alerts._outbox_path()).read_text(encoding="utf-8").strip().splitlines()
    assert len(outbox) == 1
    assert '"delivery_status": "QUEUED_NO_PROVIDER_CONFIGURED"' in outbox[0]


def test_evaluate_alerts_does_not_trigger_when_threshold_not_crossed(monkeypatch):
    alerts.create_alert("9900011122", "tomato", "kolar_apmc", "PRICE_ABOVE", 5000.0)

    class _Service:
        is_available = True

        def get_curve(self, commodity, mandi_id):
            return [{"horizon_days": 1, "status": "OK", "forecast_price": 2100.0, "decision": "HOLD"}]

    monkeypatch.setattr("mandisense_ai.forecasting.service.get_forecast_service", lambda: _Service())
    result = alerts.evaluate_alerts()
    assert result["triggered"] == 0


# ── truck sharing ───────────────────────────────────────────────────────────


def test_post_and_list_trip():
    posted = truck_share.post_trip("kolar_apmc", "2026-10-05", 50.0, "9900011122", "Ravi")
    assert posted["status"] == "OK"
    trips = truck_share.list_trips(mandi_id="kolar_apmc")
    assert len(trips) == 1
    assert trips[0]["total_capacity_quintals"] == 50.0
    assert trips[0]["status"] == "OPEN"


def test_invalid_date_is_rejected():
    result = truck_share.post_trip("kolar_apmc", "not-a-date", 50.0, "9900011122")
    assert result["status"] == "ERROR"


def test_non_positive_capacity_is_rejected():
    result = truck_share.post_trip("kolar_apmc", "2026-10-05", 0, "9900011122")
    assert result["status"] == "ERROR"


def test_join_trip_reduces_remaining_capacity():
    posted = truck_share.post_trip("kolar_apmc", "2026-10-05", 50.0, "9900011122")
    trip_id = posted["trip"]["id"]

    joined = truck_share.join_trip(trip_id, 20.0, "9900099999", "Sita")
    assert joined["status"] == "OK"
    assert joined["trip"]["claimed_quintals"] == 20.0
    assert joined["trip"]["status"] == "OPEN"


def test_join_trip_cannot_exceed_remaining_capacity():
    posted = truck_share.post_trip("kolar_apmc", "2026-10-05", 50.0, "9900011122")
    trip_id = posted["trip"]["id"]

    truck_share.join_trip(trip_id, 45.0, "9900099999")
    overdrawn = truck_share.join_trip(trip_id, 10.0, "9900088888")
    assert overdrawn["status"] == "ERROR"


def test_trip_fills_up_and_stops_being_listed_as_open():
    posted = truck_share.post_trip("kolar_apmc", "2026-10-05", 10.0, "9900011122")
    trip_id = posted["trip"]["id"]

    truck_share.join_trip(trip_id, 10.0, "9900099999")
    assert truck_share.list_trips(mandi_id="kolar_apmc") == []


def test_joining_a_nonexistent_trip_is_rejected():
    result = truck_share.join_trip("does-not-exist", 5.0, "9900099999")
    assert result["status"] == "ERROR"


def test_list_trips_filters_by_date():
    truck_share.post_trip("kolar_apmc", "2026-09-01", 10.0, "9900011122")
    truck_share.post_trip("kolar_apmc", "2026-12-01", 10.0, "9900011122")
    result = truck_share.list_trips(on_or_after="2026-10-01")
    assert len(result) == 1
    assert result[0]["travel_date"] == "2026-12-01"
