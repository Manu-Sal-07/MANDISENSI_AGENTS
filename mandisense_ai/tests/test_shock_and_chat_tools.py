"""Supply-shock service, its audience rules, and the chat tools built on it. No network."""

import pytest

from mandisense_ai.chat import tools as chat_tools
from mandisense_ai.chat.providers import _reset_seconds
from mandisense_ai.shock import service as shock

pytestmark = pytest.mark.skipif(not shock.study().get("available"), reason="shock study not built (scripts/build_shock_study.py)")


def test_farmers_only_ever_see_robust_claims():
    assert shock.FARMER_TIERS == {"ROBUST"}
    rows = shock.study_table("farmer")["results"]
    assert all(r["tier"] == "ROBUST" for r in rows)


def test_trader_table_carries_every_test_including_nulls():
    t = shock.study_table("trader")
    assert t["n_tested"] == len(t["results"]) == 30
    assert {r["tier"] for r in t["results"]} <= {"ROBUST", "SUGGESTIVE", "NONE"}
    assert all(r["min_detectable_pct"] >= 0 and r["holm_p"] is not None for r in t["results"])


def test_farmer_radar_has_no_price_claim_without_robust_evidence():
    out = shock.radar("farmer", "tomato", "kolar")
    assert out["status"] == "OK" and "cross_crop" not in out
    for item in out["items"]:
        assert item["response"] is None or item["response"]["tier"] == "ROBUST"


def test_armed_links_do_not_depend_on_the_crop_filter():
    everything = {(l["source"], l["target"], l["shock"]): l["armed_districts"] for l in shock.radar("trader")["cross_crop"]["links"]}
    narrowed = {(l["source"], l["target"], l["shock"]): l["armed_districts"] for l in shock.radar("trader", "ginger")["cross_crop"]["links"]}
    assert everything == narrowed


def test_chat_tools_respect_the_persona():
    farmer = {t.name for t in chat_tools.tools_for("farmer")}
    trader = {t.name for t in chat_tools.tools_for("trader")}
    assert {"get_best_place_to_sell", "get_supply_watch"} <= farmer and "get_shock_desk" not in farmer
    assert {"get_best_place_to_sell", "get_shock_desk"} <= trader and "get_supply_watch" not in trader
    assert chat_tools.run_tool("get_shock_desk", {}, "farmer") == {"error": "unknown tool: get_shock_desk"}


def test_trader_desk_tool_never_lists_links_without_evidence():
    out = chat_tools.run_tool("get_shock_desk", {"crop": "ginger"}, "trader")
    assert out["status"] == "OK"
    assert all(l["tier"] in {"ROBUST", "SUGGESTIVE"} for l in out["links_with_evidence"])
    assert out["battery"]["own_crop_robust"] == 0 or out["battery"]["own_crop_robust"] is not None


def test_transmission_tool_returns_compact_valid_data():
    out = chat_tools.run_tool("get_transmission_matrix", {}, "trader")
    assert "error" not in out and "truncated" not in out and len(out["edges"]) <= 14


@pytest.mark.parametrize("header,expected", [("7", 7.0), ("42.015s", 42.015), ("1m5.2s", 65.2), ("", None), ("soon", None)])
def test_rate_limit_wait_parsing(header, expected):
    assert _reset_seconds({"retry-after": header} if header else {}) == expected
