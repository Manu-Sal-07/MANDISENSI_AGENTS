"""
Standalone verification of Phase-2 Learned Ensemble.

Tests the complete pipeline:
  1. PredictionLogger (append-only JSONL logging)
  2. DatasetBuilder (feature engineering, regime classification)
  3. SimpleRidge (pure-Python ridge regression)
  4. LearnedEnsemble (training, persistence, blending)
  5. Alpha blending (Phase-1 fallback safety)

Run directly: python tests/verify_phase2.py
"""

import sys
import os
import json
import math
import types
import logging
import tempfile
import importlib.util
import shutil
from pathlib import Path

# ── Bootstrap: stub out the logger to bypass config.settings ────────
_stub_utils = types.ModuleType("utils")
_stub_logger_mod = types.ModuleType("utils.logger")

def _get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.WARNING)  # Quiet for tests
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger

_stub_logger_mod.get_logger = _get_logger
sys.modules["utils"] = _stub_utils
sys.modules["utils.logger"] = _stub_logger_mod

# ── Direct imports bypassing ensemble/__init__.py ────────────────────
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ensemble_dir = os.path.join(_parent_dir, "ensemble")


def _load_module(name, filename):
    path = os.path.join(_ensemble_dir, filename)
    spec = importlib.util.spec_from_file_location(f"ensemble.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"ensemble.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod

# Load in dependency order
_meta_mod = _load_module("meta_ensemble", "meta_ensemble.py")
_logger_mod = _load_module("prediction_logger", "prediction_logger.py")
_builder_mod = _load_module("dataset_builder", "dataset_builder.py")
_learned_mod = _load_module("learned_ensemble", "learned_ensemble.py")

PredictionLogger = _logger_mod.PredictionLogger
DatasetBuilder = _builder_mod.DatasetBuilder
FeatureRecord = _builder_mod.FeatureRecord
FEATURE_NAMES = _builder_mod.FEATURE_NAMES
extract_features = _builder_mod.extract_features
classify_regime = _builder_mod.classify_regime
SimpleRidge = _learned_mod.SimpleRidge
LearnedEnsemble = _learned_mod.LearnedEnsemble


# ── Test infrastructure ──────────────────────────────────────────────

def test(name, condition):
    status = "PASS" if condition else "FAIL"
    icon = "+" if condition else "x"
    print(f"  [{icon}] {status}  {name}")
    return condition


def generate_synthetic_records(n=100, seed=42):
    """Generate synthetic completed prediction log records for testing."""
    import random
    random.seed(seed)

    records = []
    base_timestamp = 1700000000  # ~Nov 2023

    for i in range(n):
        ts = base_timestamp + i * 86400  # one per day
        # Vary supply stress to create different regimes
        stress = random.uniform(0.0, 1.0)
        ext_impact = random.uniform(-0.5, 0.5)
        ext_conf = random.uniform(0.3, 0.8)
        s_pred = random.uniform(-8, 8)
        a_pred = random.uniform(-5, 5)
        s_conf = random.uniform(0.4, 0.9)
        a_conf = random.uniform(0.4, 0.9)
        vol = random.uniform(0.0, 0.5)

        # Simulate a vaguely reasonable actual outcome
        # Real relationship: actual ~ 0.3*norm_s + 0.5*arrival + noise
        norm_s = (s_pred / 30.0) * 7.0 * 0.8
        actual = 0.3 * norm_s + 0.5 * a_pred + random.gauss(0, 1.0)

        from datetime import datetime, timezone
        ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        records.append({
            "record_id": f"test-{i:04d}",
            "timestamp": ts_str,
            "commodity": "tomato",
            "mandi": "kolar",
            "seasonality_pred_30d": round(s_pred, 4),
            "seasonality_confidence": round(s_conf, 4),
            "seasonality_volatility": round(vol, 4),
            "seasonality_regime": random.choice(["ascending", "descending", "peak", "trough"]),
            "arrival_pred_7d": round(a_pred, 4),
            "arrival_confidence": round(a_conf, 4),
            "arrival_supply_stress": round(stress, 4),
            "arrival_regime": "squeeze" if stress > 0.8 else "normal",
            "external_impact": round(ext_impact, 4),
            "external_confidence": round(ext_conf, 4),
            "phase1_prediction": round(norm_s * 0.5 + a_pred * 0.5, 4),
            "phase1_confidence": round((s_conf + a_conf) / 2.0, 4),
            "phase1_conflict": (s_pred * a_pred < 0),
            "phase1_strong_conflict": False,
            "actual_7d_change": round(actual, 4),
            "outcome_filled_at": ts_str,
        })

    return records


def main():
    all_pass = True
    tmpdir = Path(tempfile.mkdtemp(prefix="mandisense_phase2_test_"))

    try:
        # ── 1. PredictionLogger ──────────────────────────────────────
        print("\n[1] PredictionLogger")

        log_dir = tmpdir / "logs"
        plogger = PredictionLogger(storage_dir=log_dir)

        rid = plogger.log_prediction(
            commodity="tomato", mandi="kolar",
            seasonality_pred_30d=6.0, seasonality_confidence=0.75,
            seasonality_volatility=0.3, seasonality_regime="ascending",
            arrival_pred_7d=-2.5, arrival_confidence=0.60,
            arrival_supply_stress=0.8, arrival_regime="squeeze",
            external_impact=0.4, external_confidence=0.55,
            phase1_prediction=-0.34, phase1_confidence=0.31,
            phase1_conflict=True, phase1_strong_conflict=True,
        )
        all_pass &= test("Log returns record_id", isinstance(rid, str) and len(rid) > 0)

        records = plogger.read_all()
        all_pass &= test("One record logged", len(records) == 1)
        all_pass &= test("actual starts as null", records[0]["actual_7d_change"] is None)

        # Backfill
        ts = records[0]["timestamp"]
        updated = plogger.backfill_actual("tomato", "kolar", ts, -0.5)
        all_pass &= test("Backfill updated 1 record", updated == 1)

        completed = plogger.read_completed("tomato", "kolar")
        all_pass &= test("Completed records = 1", len(completed) == 1)
        all_pass &= test("Actual value backfilled correctly", completed[0]["actual_7d_change"] == -0.5)

        # ── 2. Feature Engineering ───────────────────────────────────
        print("\n[2] Feature Engineering & Regime Classification")

        features, regime = extract_features(completed[0])
        all_pass &= test(f"Feature vector has 16 elements (got {len(features)})", len(features) == 16)
        all_pass &= test(f"Feature names has 16 entries (got {len(FEATURE_NAMES)})", len(FEATURE_NAMES) == 16)

        # norm_s = (6.0/30)*7*0.8 = 1.12
        all_pass &= test(f"norm_seasonality correct ({features[0]:.4f})", abs(features[0] - 1.12) < 0.01)
        # arrival_pred = -2.5
        all_pass &= test(f"arrival_pred correct ({features[1]:.4f})", abs(features[1] - (-2.5)) < 0.01)
        # external_score = 0.4*0.55 = 0.22
        all_pass &= test(f"external_score correct ({features[2]:.4f})", abs(features[2] - 0.22) < 0.01)

        # Regime: supply_stress=0.8 > 0.7 → supply_shock
        all_pass &= test(f"Regime = supply_shock (got {regime})", regime == "supply_shock")

        # Test normal regime
        normal_regime = classify_regime(0.3, "normal", 0.1, 1.0, 2.0)
        all_pass &= test(f"Low stress → normal (got {normal_regime})", normal_regime == "normal")

        # Test external dominated
        ext_regime = classify_regime(0.2, "normal", 0.8, 0.3, 0.2)
        all_pass &= test(f"Strong ext + weak internal → external_dominated (got {ext_regime})",
                         ext_regime == "external_dominated")

        # ── 3. SimpleRidge ───────────────────────────────────────────
        print("\n[3] SimpleRidge (Pure Python)")

        # Fit y = 2*x1 + 3*x2 + 1
        X = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0], [1.0, 2.0]]
        y = [3.0, 4.0, 6.0, 8.0, 9.0]

        ridge = SimpleRidge(alpha=0.01)  # Low regularization
        ridge.fit(X, y)

        all_pass &= test(f"Intercept near 1.0 (got {ridge.intercept_:.4f})", abs(ridge.intercept_ - 1.0) < 0.5)
        all_pass &= test(f"Coef[0] near 2.0 (got {ridge.coef_[0]:.4f})", abs(ridge.coef_[0] - 2.0) < 0.5)
        all_pass &= test(f"Coef[1] near 3.0 (got {ridge.coef_[1]:.4f})", abs(ridge.coef_[1] - 3.0) < 0.5)

        r2, mae = ridge.score(X, y)
        all_pass &= test(f"R-squared high (got {r2:.4f})", r2 > 0.95)
        all_pass &= test(f"MAE reasonable (got {mae:.4f})", mae < 0.1)

        preds = ridge.predict([[1.0, 1.0]])
        all_pass &= test(f"Prediction near 6.0 (got {preds[0]:.4f})", abs(preds[0] - 6.0) < 0.5)

        # Serialization roundtrip
        d = ridge.to_dict()
        ridge2 = SimpleRidge.from_dict(d)
        preds2 = ridge2.predict([[1.0, 1.0]])
        all_pass &= test("Serialization roundtrip preserves predictions", abs(preds[0] - preds2[0]) < 1e-6)

        # ── 4. DatasetBuilder ────────────────────────────────────────
        print("\n[4] DatasetBuilder")

        synthetic = generate_synthetic_records(n=100)
        builder = DatasetBuilder(min_total=50, min_per_regime=10)
        result = builder.build(synthetic)

        all_pass &= test("100 records are trainable", result["trainable"] is True)
        all_pass &= test(f"Total records = 100 (got {result['total']})", result["total"] == 100)
        all_pass &= test("At least 'normal' in trainable regimes", "normal" in result["trainable_regimes"])
        all_pass &= test(f"Regime counts exist", len(result["regime_counts"]) > 0)

        # Walk-forward splits
        splits = builder.walk_forward_splits(result["records"], n_splits=3)
        all_pass &= test(f"Walk-forward generated splits (got {len(splits)})", len(splits) > 0)
        if splits:
            train_set, val_set = splits[0]
            all_pass &= test(f"Train set size reasonable (got {len(train_set)})", len(train_set) >= 30)
            all_pass &= test(f"Val set size > 0 (got {len(val_set)})", len(val_set) > 0)

        # Insufficient data
        small_result = builder.build(synthetic[:20])
        all_pass &= test("20 records not trainable", small_result["trainable"] is False)

        # ── 5. LearnedEnsemble Training ──────────────────────────────
        print("\n[5] LearnedEnsemble Training & Persistence")

        model_dir = tmpdir / "models"
        ensemble = LearnedEnsemble(model_dir=model_dir)
        report = ensemble.train(result["records"], result["trainable_regimes"])

        all_pass &= test("Training report has regimes", "regimes" in report)
        all_pass &= test("At least one model trained", len(ensemble.models) > 0)
        all_pass &= test("Ensemble is ready", ensemble.is_ready)

        # Check normal model exists
        if "normal" in ensemble.models:
            m = ensemble.models["normal"]
            all_pass &= test(f"Normal model R2_train > 0 (got {m.r2_train:.4f})", m.r2_train > 0)
            all_pass &= test(f"Normal model has 16 coefficients (got {len(m.model.coef_)})",
                             len(m.model.coef_) == 16)

        # Save & reload
        ensemble.save()
        ensemble2 = LearnedEnsemble(model_dir=model_dir)
        loaded = ensemble2.load()
        all_pass &= test("Models loaded from disk", loaded is True)
        all_pass &= test("Same number of models after reload",
                         len(ensemble2.models) == len(ensemble.models))

        # ── 6. Inference & Blending ──────────────────────────────────
        print("\n[6] Inference & Alpha Blending")

        blend_result = ensemble.predict_and_blend(
            seasonality_pred_30d=6.0, seasonality_confidence=0.75,
            seasonality_volatility=0.3, seasonality_regime="ascending",
            arrival_pred_7d=-2.5, arrival_confidence=0.60,
            arrival_supply_stress=0.8, arrival_regime="squeeze",
            external_impact=0.4, external_confidence=0.55,
            phase1_prediction=-0.34, phase1_confidence=0.31,
        )

        all_pass &= test(f"Mode is 'blended' (got {blend_result['mode']})",
                         blend_result["mode"] == "blended")
        all_pass &= test(f"Alpha in [0.3, 1.0] (got {blend_result['alpha']:.4f})",
                         0.3 <= blend_result["alpha"] <= 1.0)
        all_pass &= test(f"Learned residual is present",
                         "learned_residual" in blend_result)
        all_pass &= test(f"Final prediction clamped (got {blend_result['final_prediction']:.4f})",
                         -15.0 <= blend_result["final_prediction"] <= 15.0)
        all_pass &= test(f"Final confidence in [0.05, 0.95] (got {blend_result['final_confidence']:.4f})",
                         0.05 <= blend_result["final_confidence"] <= 0.95)
        all_pass &= test(f"Regime detected", len(blend_result["regime_detected"]) > 0)

        # Model stats present (Soft Blending)
        all_pass &= test("Soft regime weights included", "soft_regime_weights" in blend_result)
        all_pass &= test("Model stats included", "model_stats" in blend_result)
        if blend_result.get("model_stats"):
            first_stat = list(blend_result["model_stats"].values())[0]
            all_pass &= test("Model stats have R2", "r2_val" in first_stat)

        # ── 7. Fallback Safety ───────────────────────────────────────
        print("\n[7] Fallback Safety")

        empty_ensemble = LearnedEnsemble(model_dir=tmpdir / "empty_models")
        fallback_result = empty_ensemble.predict_and_blend(
            seasonality_pred_30d=6.0, seasonality_confidence=0.75,
            seasonality_volatility=0.3, seasonality_regime="ascending",
            arrival_pred_7d=-2.5, arrival_confidence=0.60,
            arrival_supply_stress=0.8, arrival_regime="squeeze",
            external_impact=0.4, external_confidence=0.55,
            phase1_prediction=-0.34, phase1_confidence=0.31,
        )

        all_pass &= test(f"No model → phase1_only (got {fallback_result['mode']})",
                         fallback_result["mode"] == "phase1_only")
        all_pass &= test(f"Alpha = 1.0 (got {fallback_result['alpha']:.4f})",
                         fallback_result["alpha"] == 1.0)
        all_pass &= test(f"Prediction = Phase-1 prediction (got {fallback_result['final_prediction']:.4f})",
                         abs(fallback_result["final_prediction"] - (-0.34)) < 0.01)
        all_pass &= test("Learned residual is 0.0 in fallback", fallback_result.get("learned_residual") == 0.0)

        # ── 8. Determinism ───────────────────────────────────────────
        print("\n[8] Determinism")

        results = [
            ensemble.predict_and_blend(
                seasonality_pred_30d=6.0, seasonality_confidence=0.75,
                seasonality_volatility=0.3, seasonality_regime="ascending",
                arrival_pred_7d=-2.5, arrival_confidence=0.60,
                arrival_supply_stress=0.8, arrival_regime="squeeze",
                external_impact=0.4, external_confidence=0.55,
                phase1_prediction=-0.34, phase1_confidence=0.31,
            )
            for _ in range(5)
        ]
        preds = [r["final_prediction"] for r in results]
        all_pass &= test("5 identical calls produce identical results",
                         all(p == preds[0] for p in preds))

        # ── Summary ──────────────────────────────────────────────────
        print(f"\n{'='*60}")
        if all_pass:
            print("ALL TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
        print(f"{'='*60}\n")

    finally:
        # Cleanup temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
