"""Insights on the market-choice engine: the arithmetic must reproduce the served advice, and the scenarios must behave."""

import pytest

from mandisense_ai.market_choice import insights, service
from mandisense_ai.market_choice.config import ARTIFACT_DIR

pytestmark = pytest.mark.skipif(not (ARTIFACT_DIR / "tomato" / "meta.json").exists(), reason="market-choice engines not built")

ORIGIN = service.resolve_origin("kolar", None, None, None)


def test_breakdown_adds_up_to_the_served_net_revenue():
    b = insights.breakdown("tomato", ORIGIN, 10)
    rec = service.recommend("tomato", ORIGIN, 10)
    assert b["status"] == "OK"
    assert abs(b["options"]["recommended"]["net"] - rec["recommended"]["expected_net_per_q"]) <= 1
    for o in b["options"].values():
        assert abs(sum(p["value"] for p in o["parts"]) - o["net"]) <= 1.0     # the parts are the whole story
    assert [p["key"] for p in b["options"]["farm_gate"]["parts"]] == ["price", "farm_gate_discount"]


def test_default_costs_reproduce_the_served_recommendation():
    s = insights.simulate("tomato", ORIGIN, 10)
    rec = service.recommend("tomato", ORIGIN, 10)
    assert not s["changed"]
    assert s["recommended"]["mandi_id"] == rec["recommended"]["mandi_id"]
    assert s["recommended"]["hold_days"] == rec["recommended"]["hold_days"]


def test_forbidding_waiting_never_returns_a_hold():
    assert insights.simulate("tomato", ORIGIN, 10, max_hold=0)["recommended"]["hold_days"] == 0


def test_dearer_transport_never_lengthens_the_trip():
    cheap = insights.simulate("tomato", ORIGIN, 10, transport=0.1)["recommended"]
    dear = insights.simulate("tomato", ORIGIN, 10, transport=3.0)["recommended"]
    assert dear["distance_km"] <= cheap["distance_km"]


def test_flips_point_at_a_real_change():
    s = insights.simulate("tomato", ORIGIN, 10)
    for sweep in s["sweeps"].values():
        pts = sweep["points"]
        for f in sweep["flips"]:
            i = next(i for i, p in enumerate(pts) if p["x"] == f["at"])
            assert (pts[i]["mandi_id"], pts[i]["hold_days"]) != (pts[i - 1]["mandi_id"], pts[i - 1]["hold_days"])


def test_a_crowd_of_one_is_the_single_farmer_advice():
    c = insights.crowd("tomato", ORIGIN, farmers=1, quantity=10)
    assert abs(c["everyone_follows_best"]["net_per_q"] - c["alone"]["net_per_q"]) <= 40     # 10 quintals barely moves a yard


def test_coordination_never_loses_to_everyone_following_the_best_action():
    for n in (20, 200, 2000):
        c = insights.crowd("tomato", ORIGIN, farmers=n, quantity=10)
        assert c["coordinated"]["net_per_q"] >= c["everyone_follows_best"]["net_per_q"] - 1
        assert abs(sum(r["share"] for r in c["coordinated"]["split"]) - 1) < 0.02


def test_no_price_impact_means_everyone_can_follow_the_best_action():
    c = insights.crowd("tomato", ORIGIN, farmers=500, quantity=10, flexibility=0.0)
    assert abs(c["everyone_follows_best"]["net_per_q"] - c["alone"]["net_per_q"]) <= 1
    assert c["everyone_follows_best"]["price_drop_pct"] == 0


def test_reporting_value_treats_a_weekly_closure_as_known():
    r = insights.reporting_value("tomato")
    assert r["status"] == "OK" and r["mandis"]
    for m in r["mandis"]:
        assert 0 <= m["silent_share_open_days"] <= 1 and 0 <= m["reported_share"] <= 1
        assert len(m["silent_by_weekday"]) == 7
    assert any("Sunday" in m["closed_weekdays"] for m in r["mandis"])
    losses = [m["expected_loss_per_q"] for m in r["mandis"]]
    assert losses == sorted(losses, reverse=True)


def test_track_record_shares_are_proper_fractions():
    t = insights.track_record("tomato")
    if t["status"] != "OK":
        pytest.skip("track record not built")
    for w in ("last60", "all"):
        for k in ("vs_nearest", "vs_highest_yesterday"):
            x = t[w][k]
            assert abs(x["win"] + x["tie"] + x["loss"] - 1) < 0.01
    assert t["all"]["days"] >= 60


def test_unserved_crop_is_refused_everywhere():
    assert insights.breakdown("garlic", ORIGIN)["status"] == "UNAVAILABLE"
    assert insights.simulate("garlic", ORIGIN)["status"] == "UNAVAILABLE"
    assert insights.crowd("garlic", ORIGIN)["status"] == "UNAVAILABLE"
    assert insights.track_record("garlic")["status"] == "UNAVAILABLE"
