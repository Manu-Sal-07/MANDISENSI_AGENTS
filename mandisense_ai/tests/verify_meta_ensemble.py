"""
Standalone verification of Meta-Ensemble fusion logic.

This script validates the core fusion engine without requiring
the full MandiSense dependency stack (pydantic_settings, etc).
Run directly: python tests/verify_meta_ensemble.py
"""

import sys
import os
import types
import logging
import importlib.util

# ── Bootstrap: stub out the logger to avoid config.settings chain ────
_stub_utils = types.ModuleType("utils")
_stub_logger_mod = types.ModuleType("utils.logger")

def _get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger

_stub_logger_mod.get_logger = _get_logger
sys.modules["utils"] = _stub_utils
sys.modules["utils.logger"] = _stub_logger_mod

# ── Direct import of meta_ensemble.py (bypasses ensemble/__init__.py) ─
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_meta_path = os.path.join(_parent_dir, "ensemble", "meta_ensemble.py")
spec = importlib.util.spec_from_file_location("ensemble.meta_ensemble", _meta_path)
meta_mod = importlib.util.module_from_spec(spec)
sys.modules["ensemble.meta_ensemble"] = meta_mod
spec.loader.exec_module(meta_mod)

SeasonalityInput = meta_mod.SeasonalityInput
ArrivalInput = meta_mod.ArrivalInput
ExternalInput = meta_mod.ExternalInput
fuse = meta_mod.fuse
_safe_float = meta_mod._safe_float
_clamp = meta_mod._clamp
_sign = meta_mod._sign


def test(name, condition):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status}  {name}")
    return condition


def main():
    all_pass = True
    
    # ── Utility Tests ─────────────────────────────────────────────
    print("\n🔧 Utility Functions")
    all_pass &= test("safe_float(3.14) → 3.14", _safe_float(3.14) == 3.14)
    all_pass &= test("safe_float(None) → 0.0", _safe_float(None) == 0.0)
    all_pass &= test("safe_float(NaN) → 0.0", _safe_float(float("nan")) == 0.0)
    all_pass &= test("safe_float(inf) → 0.0", _safe_float(float("inf")) == 0.0)
    all_pass &= test("clamp(5, 0, 1) → 1", _clamp(5, 0, 1) == 1.0)
    all_pass &= test("clamp(-5, 0, 1) → 0", _clamp(-5, 0, 1) == 0.0)
    all_pass &= test("sign(3.5) → +1", _sign(3.5) == 1)
    all_pass &= test("sign(-0.1) → -1", _sign(-0.1) == -1)
    all_pass &= test("sign(0) → 0", _sign(0.0) == 0)

    # ── Input Validation ──────────────────────────────────────────
    print("\n🛡️  Input Validation")
    s = SeasonalityInput(confidence=1.5)
    all_pass &= test("Confidence clamped to 1.0", s.confidence == 1.0)
    
    a = ArrivalInput(supply_stress=-0.5)
    all_pass &= test("supply_stress clamped to 0.0", a.supply_stress == 0.0)
    
    e = ExternalInput(impact_score=5.0)
    all_pass &= test("impact_score clamped to 1.0", e.impact_score == 1.0)
    
    s2 = SeasonalityInput(regime="  ASCENDING  ")
    all_pass &= test("Regime normalized to lowercase", s2.regime == "ascending")

    # ── Worked Example from Design Doc ────────────────────────────
    print("\n📊 Worked Example (Design Doc)")
    s_ex = SeasonalityInput(prediction_30d=6.0, confidence=0.75, volatility=0.3, regime="ascending")
    a_ex = ArrivalInput(prediction_7d=-2.5, confidence=0.60, supply_stress=0.8, regime="squeeze")
    e_ex = ExternalInput(impact_score=0.4, confidence=0.55)
    
    result = fuse(s_ex, a_ex, e_ex)
    
    all_pass &= test("Conflict detected (opposite signs)", result.risk_flags["conflict_detected"] is True)
    all_pass &= test("Strong conflict detected (magnitude divergence)", result.risk_flags["strong_conflict"] is True)
    all_pass &= test(f"Prediction significantly dampened (got {result.final_prediction:.4f})", abs(result.final_prediction) < 1.0)
    all_pass &= test(f"Confidence heavily penalized (got {result.final_confidence:.4f})", result.final_confidence < 0.35)
    attr_sum = sum(result.attribution.values())
    all_pass &= test(f"Attribution sums to ~100% (got {attr_sum:.1f})", abs(attr_sum - 100) < 0.5)
    all_pass &= test("Arrival has higher attribution (due to magnitude)", result.attribution["arrival_pct"] > result.attribution["seasonality_pct"])

    # ── Agreement Scenario ────────────────────────────────────────
    print("\n🤝 Agreement Scenario")
    s_agree = SeasonalityInput(prediction_30d=9.0, confidence=0.80, volatility=0.1, regime="ascending")
    a_agree = ArrivalInput(prediction_7d=3.0, confidence=0.70, supply_stress=0.2, regime="normal")
    e_agree = ExternalInput(impact_score=0.3, confidence=0.5)
    
    result_agree = fuse(s_agree, a_agree, e_agree)
    
    all_pass &= test("No conflict detected", result_agree.risk_flags["conflict_detected"] is False)
    all_pass &= test(f"Positive prediction (got {result_agree.final_prediction:.4f})", result_agree.final_prediction > 0)
    all_pass &= test(f"Confidence preserved (got {result_agree.final_confidence:.4f})", result_agree.final_confidence > 0.6)

    # ── Edge Cases ────────────────────────────────────────────────
    print("\n⚠️  Edge Cases")
    
    # All zeros
    result_zero = fuse(SeasonalityInput(), ArrivalInput(), ExternalInput())
    all_pass &= test(f"All zeros → pred=0 (got {result_zero.final_prediction})", result_zero.final_prediction == 0.0)
    all_pass &= test(f"All zeros → conf ≥ 0.05 (got {result_zero.final_confidence})", result_zero.final_confidence >= 0.05)
    
    # Extreme prediction clamped
    result_extreme = fuse(
        SeasonalityInput(prediction_30d=200.0, confidence=0.90),
        ArrivalInput(prediction_7d=50.0, confidence=0.90),
        ExternalInput()
    )
    all_pass &= test(f"Extreme clamped to ≤15 (got {result_extreme.final_prediction})", result_extreme.final_prediction <= 15.0)
    
    # Both low confidence
    result_low = fuse(
        SeasonalityInput(prediction_30d=5.0, confidence=0.15),
        ArrivalInput(prediction_7d=3.0, confidence=0.20),
        ExternalInput()
    )
    all_pass &= test("Both low conf → low_confidence flag", result_low.risk_flags["low_confidence"] is True)
    
    # Perfect confidence capped
    result_perf = fuse(
        SeasonalityInput(prediction_30d=5.0, confidence=1.0, regime="ascending"),
        ArrivalInput(prediction_7d=2.0, confidence=1.0),
        ExternalInput(impact_score=0.5, confidence=1.0)
    )
    all_pass &= test(f"Perfect inputs → conf ≤ 0.95 (got {result_perf.final_confidence})", result_perf.final_confidence <= 0.95)

    # ── Dynamic Weights ───────────────────────────────────────────
    print("\n⚖️  Dynamic Weight Tests")
    
    # High supply stress boosts Arrival
    result_stress = fuse(
        SeasonalityInput(prediction_30d=7.0, confidence=0.70, volatility=0.0, regime="neutral"),
        ArrivalInput(prediction_7d=3.0, confidence=0.70, supply_stress=0.9, regime="squeeze"),
        ExternalInput()
    )
    all_pass &= test(
        f"Weight Stability: Arrival weight capped at ~0.6 (got {result_stress.debug['w_a_final']:.4f})",
        abs(result_stress.debug["w_a_final"] - 0.6) < 0.01
    )
    
    # Trend regime boosts Seasonality
    result_trend = fuse(
        SeasonalityInput(prediction_30d=10.0, confidence=0.50, volatility=0.0, regime="ascending"),
        ArrivalInput(prediction_7d=1.0, confidence=0.50, supply_stress=0.0, regime="normal"),
        ExternalInput()
    )
    result_neutral = fuse(
        SeasonalityInput(prediction_30d=1.0, confidence=0.50, volatility=0.0, regime="trough"),
        ArrivalInput(prediction_7d=1.0, confidence=0.50, supply_stress=0.0, regime="normal"),
        ExternalInput()
    )
    all_pass &= test(
        f"Signal Strength + Trend boost → higher S weight ({result_trend.debug['w_s_final']:.4f} > {result_neutral.debug['w_s_final']:.4f})",
        result_trend.debug["w_s_final"] > result_neutral.debug["w_s_final"]
    )

    # ── Determinism ───────────────────────────────────────────────
    print("\n🔁 Determinism")
    s_det = SeasonalityInput(prediction_30d=4.5, confidence=0.65, volatility=0.2, regime="ascending")
    a_det = ArrivalInput(prediction_7d=-1.0, confidence=0.55, supply_stress=0.4, regime="normal")
    e_det = ExternalInput(impact_score=0.2, confidence=0.4)
    
    results = [fuse(s_det, a_det, e_det) for _ in range(10)]
    preds_same = all(r.final_prediction == results[0].final_prediction for r in results)
    confs_same = all(r.final_confidence == results[0].final_confidence for r in results)
    all_pass &= test("10 identical calls → identical predictions", preds_same)
    all_pass &= test("10 identical calls → identical confidences", confs_same)

    # ── Output Schema ─────────────────────────────────────────────
    print("\n📋 Output Schema")
    result_schema = fuse(
        SeasonalityInput(prediction_30d=5.0, confidence=0.70),
        ArrivalInput(prediction_7d=2.0, confidence=0.60),
        ExternalInput(impact_score=0.3, confidence=0.5)
    )
    d = result_schema.to_dict()
    all_pass &= test("to_dict has 'final_prediction'", "final_prediction" in d)
    all_pass &= test("to_dict has 'final_confidence'", "final_confidence" in d)
    all_pass &= test("to_dict has 'attribution'", "attribution" in d)
    all_pass &= test("to_dict has 'risk_flags'", "risk_flags" in d)
    all_pass &= test("to_dict excludes 'debug'", "debug" not in d)
    all_pass &= test("Attribution has 3 keys", len(d["attribution"]) == 3)

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if all_pass:
        print("🎉 ALL TESTS PASSED")
    else:
        print("💥 SOME TESTS FAILED")
    print(f"{'='*60}\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
