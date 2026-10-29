"""Guardrails of the farmer explanation: the model may only paraphrase, never change facts, numbers or the decision.

No network: these test the validators and the rule-based path.
"""

import pytest

from mandisense_ai.intelligence import explain as ex


def _rec(**over):
    rec = {
        "status": "OK", "crop": "tomato", "alpha": 0.1, "confidence_pct": 90, "decision_day": "2026-10-27", "quantity_quintals": 20,
        "recommended": {"kind": "mandi", "mandi_name": "Ramanagara", "mandi_name_kn": "ರಾಮನಗರ", "mandi_name_hi": "रामनगर", "hold_days": 1,
                        "sale_date": "2026-10-28", "distance_km": 103.2, "expected_net_per_q": 1824.0, "floor_per_q": 1316.0, "chance_open": 0.97},
        "baselines": {"nearest_today": {"kind": "mandi", "mandi_name": "Kolar", "mandi_name_kn": "ಕೋಲಾರ", "mandi_name_hi": "कोलार",
                                        "expected_net_per_q": 1232.0}},
        "gain": {"vs_nearest_per_q": 592.0}, "guarantee": {"backtest_violation": 0.096},
        "evidence": {"status": "OK", "level": "strong", "scored_days": 330, "gain_vs_highest_yesterday": {"mean": 170.0}},
        "caveats": [], "origin": {"lat": 13.1, "lon": 78.1},
    }
    rec.update(over)
    return rec


SRC = "After transport, this leaves you {gain.nearest} per quintal {gain.nearest_dir} than going to {nearest.mandi}."


def test_paraphrase_must_keep_exactly_the_same_placeholders():
    ok = "Compared with going to {nearest.mandi}, you keep {gain.nearest} per quintal {gain.nearest_dir}."
    assert ex.validate_paraphrase(SRC, ok, "en") is None
    assert ex.validate_paraphrase(SRC, "You keep {gain.nearest} per quintal {gain.nearest_dir}.", "en") == "placeholders_changed"          # dropped one
    assert ex.validate_paraphrase(SRC, ok + " {best.net}", "en") == "placeholders_changed"                                                # added one
    assert ex.validate_paraphrase(SRC, ok.replace("{nearest.mandi}", "{best.mandi}"), "en") == "placeholders_changed"                    # swapped meaning


def test_paraphrase_may_not_introduce_digits_or_overclaims():
    assert ex.validate_paraphrase(SRC, "You keep {gain.nearest} per quintal {gain.nearest_dir} than {nearest.mandi}, about 20 more.", "en") == "contains_digit"
    assert ex.validate_paraphrase(SRC, "This is guaranteed: {gain.nearest} {gain.nearest_dir} than {nearest.mandi}.", "en") == "overclaim"
    assert ex.validate_paraphrase(SRC, "You will definitely keep {gain.nearest} {gain.nearest_dir} than {nearest.mandi}.", "en") == "overclaim"
    assert ex.validate_paraphrase(SRC, " ".join(["word"] * 60) + " {gain.nearest} {gain.nearest_dir} {nearest.mandi}", "en") == "too_long"


def test_paraphrase_must_be_in_the_requested_script():
    kn_src = "{nearest.mandi} ಮಂಡಿಗೆ ಹೋಗುವುದಕ್ಕಿಂತ {gain.nearest} {gain.nearest_dir} ಉಳಿಯುತ್ತದೆ."
    assert ex.validate_paraphrase(kn_src, kn_src, "kn") is None
    assert ex.validate_paraphrase(kn_src, "You keep {gain.nearest} {gain.nearest_dir} than {nearest.mandi}.", "kn") == "wrong_language"
    assert ex.validate_paraphrase(SRC, "{nearest.mandi} ಮಂಡಿಗೆ {gain.nearest} {gain.nearest_dir}", "en") == "wrong_language"


@pytest.mark.parametrize("lang", ["en", "kn", "hi"])
def test_headline_is_composed_by_code_from_the_recommendation(lang):
    out = ex.explain(_rec(), None, lang, use_llm=False)
    best = _rec()["recommended"]
    assert "₹1,824" in out["headline"] and "₹1,316" in out["headline"] and "90%" in out["headline"]
    assert out["author"] == "rules" and out["checks"]["decision_unchanged"]
    names = {"en": best["mandi_name"], "kn": best["mandi_name_kn"], "hi": best["mandi_name_hi"]}
    assert names[lang] in out["headline"]


def test_numbers_use_indian_grouping():
    assert ex._indian(1824) == "₹1,824"
    assert ex._indian(125943) == "₹1,25,943"
    assert ex._indian(12594) == "₹12,594"


def test_track_record_is_only_stated_when_the_evidence_is_strong():
    strong = ex.build_facts(_rec(), None, "en")
    assert "track.gain" in strong
    limited = ex.build_facts(_rec(evidence={"status": "OK", "level": "limited", "scored_days": 330,
                                            "gain_vs_highest_yesterday": {"mean": 15.0}}), None, "en")
    assert "track.gain" not in limited
    negative = ex.build_facts(_rec(evidence={"status": "OK", "level": "strong", "scored_days": 330,
                                             "gain_vs_highest_yesterday": {"mean": -10.0}}), None, "en")
    assert "track.gain" not in negative


def test_caveats_always_become_cautions():
    out = ex.explain(_rec(caveats=["limited_evidence", "sale_on_sunday"]), None, "en", use_llm=False)
    joined = " ".join(out["cautions"]).lower()
    assert "guide" in joined and "sunday" in joined


def test_price_response_claims_need_a_robust_tier():
    base = {"arrivals": {"state": "glut", "direction": "glut", "times_normal": 2.1, "age_days": 0}, "gap": None}
    robust = dict(base, response={"tier": "ROBUST", "typical_change_pct": -6.0, "horizon_days": 7})
    suggestive = dict(base, response={"tier": "SUGGESTIVE", "typical_change_pct": -6.0, "horizon_days": 7})
    assert "resp.pct" in ex.build_facts(_rec(), robust, "en")
    assert "resp.pct" not in ex.build_facts(_rec(), suggestive, "en")
    assert "shock.state" in ex.build_facts(_rec(), suggestive, "en")       # the observation (arrivals) is always shown


def test_stale_arrival_readings_are_not_reported_as_live():
    stale = {"arrivals": {"state": "glut", "direction": "glut", "times_normal": 2.1, "age_days": 30}, "gap": None}
    assert "shock.state" not in ex.build_facts(_rec(), stale, "en")


def test_unavailable_model_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(ex, "load_env", lambda: None)
    monkeypatch.setattr(ex, "_llm_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network down")))
    ex._CACHE.clear()
    out = ex.explain(_rec(), None, "en", use_llm=True)
    assert out["author"] == "rules" and "llm_error" in out["checks"] and out["why"]


def test_judge_rejection_reverts_a_sentence_to_the_rule_based_wording(monkeypatch):
    facts = ex.build_facts(_rec(), None, "en")
    base = ex.rule_templates(facts, [], "en")
    rewrites = {"sentences": [{"id": f"w{i}", "text": t} for i, t in enumerate(base["why"])]}
    monkeypatch.setattr(ex, "_llm_json", lambda *a, **k: (rewrites, "stub"))
    monkeypatch.setattr(ex, "judge_faithful", lambda pairs, lang, model=None: {p["id"]: {"faithful": p["id"] != "w0", "problem": "reversed"} for p in pairs})
    got = ex.llm_explain(base, facts, "en")
    assert got["n_llm"] == len(base["why"]) - 1
    assert any(r["reason"].startswith("judge:") for r in got["rejected"])
    assert got["why"][0] == ex._fill(base["why"][0], facts)
