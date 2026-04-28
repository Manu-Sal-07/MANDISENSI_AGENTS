"""
Background Tasks — Model Retraining Pipeline.

Provides both a Celery task interface and a standalone CLI entry point
for retraining the Phase-2.5 Ridge models.

Usage:
  CLI:    python -m tasks.retraining
  Celery: retrain_models.delay()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def run_retraining(min_total: int = 50, min_per_regime: int = 20) -> dict:
    """
    Execute the full retraining pipeline.

    Steps:
      1. Load completed prediction logs
      2. Build features + residual targets via DatasetBuilder
      3. Train per-regime Ridge models with walk-forward validation
      4. Compare against current models (if any)
      5. Save new models if improved (or if first training)

    Returns:
        Training report dict
    """
    from ensemble.prediction_logger import PredictionLogger
    from ensemble.dataset_builder import DatasetBuilder
    from ensemble.learned_ensemble import LearnedEnsemble

    logger.info("[Retraining] Starting model retraining pipeline...")

    # 1. Load data
    plogger = PredictionLogger()
    records = plogger.read_completed()
    logger.info(f"[Retraining] Found {len(records)} completed prediction records")

    # 2. Build dataset
    builder = DatasetBuilder(min_total=min_total, min_per_regime=min_per_regime)
    result = builder.build(records)

    if not result["trainable"]:
        msg = f"Not enough data to train: {result['reason']}"
        logger.warning(f"[Retraining] {msg}")
        return {"status": "skipped", "reason": msg}

    logger.info(
        f"[Retraining] Dataset built: {result['total']} records, "
        f"regimes={result['regime_counts']}, "
        f"trainable={result['trainable_regimes']}"
    )

    # 3. Load existing models for comparison
    current = LearnedEnsemble()
    has_current = current.load()
    current_r2 = {}
    if has_current:
        for regime, m in current.models.items():
            current_r2[regime] = m.r2_val

    # 4. Train new models
    new_ensemble = LearnedEnsemble()
    report = new_ensemble.train(result["records"], result["trainable_regimes"])

    # 5. Compare and decide
    improved = False
    comparison = {}
    for regime, info in report.get("regimes", {}).items():
        if isinstance(info, dict) and "r2_val" in info and info["r2_val"] is not None:
            old_r2 = current_r2.get(regime, -999.0)
            new_r2 = info["r2_val"]
            comparison[regime] = {
                "old_r2": round(old_r2, 4),
                "new_r2": round(new_r2, 4),
                "improved": new_r2 >= old_r2,
            }
            if new_r2 >= old_r2:
                improved = True

    # Save if any improvement or first training
    if improved or not has_current:
        new_ensemble.save()
        status = "trained_and_saved"
        logger.info(f"[Retraining] New models saved. Comparison: {comparison}")
    else:
        status = "trained_but_not_promoted"
        logger.info(f"[Retraining] New models not better. Keeping current. Comparison: {comparison}")

    report["status"] = status
    report["comparison"] = comparison
    report["total_records_used"] = result["total"]

    return report


# ── CLI Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    report = run_retraining()
    print(json.dumps(report, indent=2, default=str))
    sys.exit(0 if report.get("status") != "skipped" else 1)
