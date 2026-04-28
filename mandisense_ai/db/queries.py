"""
Production Query Library — Optimized PostgreSQL queries for MandiSense.

All common query patterns in one place. Each function documents
which index it uses and expected performance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Prediction Queries
# ═══════════════════════════════════════════════════════════════════════════════

LATEST_PREDICTION = """
-- Latest prediction for a commodity/mandi pair
-- Uses: idx_pred_commodity_time (commodity, mandi, created_at DESC)
-- Expected: < 1ms (index seek)
SELECT record_id, created_at, commodity, mandi,
       phase1_prediction, phase1_confidence,
       final_prediction, final_confidence,
       alpha, regime_detected, blend_mode,
       actual_7d_change
FROM prediction_log
WHERE commodity = %s AND mandi = %s
ORDER BY created_at DESC
LIMIT 1;
"""

PREDICTION_HISTORY = """
-- Prediction history for a commodity/mandi over N days
-- Uses: idx_pred_commodity_time
-- Expected: < 5ms for 30 days
SELECT record_id, created_at, commodity, mandi,
       phase1_prediction, phase1_confidence,
       final_prediction, final_confidence,
       alpha, regime_detected,
       actual_7d_change
FROM prediction_log
WHERE commodity = %s AND mandi = %s
  AND created_at >= NOW() - INTERVAL '%s days'
ORDER BY created_at DESC;
"""

UNFILLED_PREDICTIONS = """
-- Records needing backfill (older than 7 days, no actual)
-- Uses: idx_pred_unfilled (partial index on actual_7d_change IS NULL)
-- Expected: < 5ms
SELECT record_id, created_at, commodity, mandi
FROM prediction_log
WHERE actual_7d_change IS NULL
  AND created_at < NOW() - INTERVAL '7 days'
ORDER BY created_at ASC
LIMIT 500;
"""

COMPLETED_FOR_TRAINING = """
-- All completed records for model training
-- Uses: idx_pred_completed (partial index on actual_7d_change IS NOT NULL)
-- Expected: ~10ms for 1000 records
SELECT record_id, created_at, commodity, mandi,
       seasonality_pred_30d, seasonality_confidence,
       seasonality_volatility, seasonality_regime,
       arrival_pred_7d, arrival_confidence,
       arrival_supply_stress, arrival_regime,
       external_impact, external_confidence,
       phase1_prediction, phase1_confidence,
       phase1_conflict, phase1_strong_conflict,
       actual_7d_change
FROM prediction_log
WHERE actual_7d_change IS NOT NULL
ORDER BY created_at ASC;
"""

BACKFILL_ACTUAL = """
-- Backfill actual outcome for a specific date
-- Uses: idx_pred_unfilled
-- Expected: < 2ms
UPDATE prediction_log
SET actual_7d_change = %s,
    outcome_filled_at = NOW()
WHERE commodity = %s
  AND mandi = %s
  AND created_at::date = %s::date
  AND actual_7d_change IS NULL;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Model Performance Queries
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_ACCURACY_SUMMARY = """
-- Calculate MAE and directional accuracy for a commodity/mandi
-- over the last N days where actuals are available
-- Uses: idx_pred_completed
SELECT
    COUNT(*) AS total_predictions,
    AVG(ABS(phase1_prediction - actual_7d_change)) AS mae_phase1,
    AVG(ABS(COALESCE(final_prediction, phase1_prediction) - actual_7d_change)) AS mae_final,
    AVG(CASE
        WHEN SIGN(COALESCE(final_prediction, phase1_prediction)) = SIGN(actual_7d_change)
        THEN 1.0 ELSE 0.0
    END) AS directional_accuracy,
    AVG(final_confidence) AS avg_confidence
FROM prediction_log
WHERE commodity = %s AND mandi = %s
  AND actual_7d_change IS NOT NULL
  AND created_at >= NOW() - INTERVAL '%s days';
"""

PREDICTION_ERROR_DISTRIBUTION = """
-- Error distribution by regime (for drift detection)
SELECT
    regime_detected,
    COUNT(*) AS n,
    AVG(ABS(COALESCE(final_prediction, phase1_prediction) - actual_7d_change)) AS mae,
    STDDEV(COALESCE(final_prediction, phase1_prediction) - actual_7d_change) AS error_std
FROM prediction_log
WHERE actual_7d_change IS NOT NULL
  AND created_at >= NOW() - INTERVAL '%s days'
GROUP BY regime_detected
ORDER BY n DESC;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Market Data Queries
# ═══════════════════════════════════════════════════════════════════════════════

UPSERT_MARKET_PRICE = """
-- Idempotent price insert (daily price per commodity/mandi)
-- Uses: uq_market_price UNIQUE constraint
INSERT INTO market_prices (commodity, mandi, price_date, modal_price, min_price, max_price)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (commodity, mandi, price_date)
DO UPDATE SET
    modal_price = EXCLUDED.modal_price,
    min_price = EXCLUDED.min_price,
    max_price = EXCLUDED.max_price;
"""

PRICE_RANGE = """
-- Price history for a commodity/mandi over N days
-- Uses: idx_prices_lookup
SELECT price_date, modal_price, min_price, max_price
FROM market_prices
WHERE commodity = %s AND mandi = %s
  AND price_date >= CURRENT_DATE - %s
ORDER BY price_date DESC;
"""

COMPUTE_7D_CHANGE = """
-- Compute actual 7-day price change for backfill
-- Uses: idx_prices_lookup (two seeks)
SELECT
    p1.modal_price AS price_t0,
    p2.modal_price AS price_t7,
    CASE WHEN p1.modal_price > 0
         THEN ((p2.modal_price - p1.modal_price) / p1.modal_price) * 100.0
         ELSE NULL
    END AS pct_change_7d
FROM market_prices p1
JOIN market_prices p2
  ON p1.commodity = p2.commodity
  AND p1.mandi = p2.mandi
  AND p2.price_date = p1.price_date + INTERVAL '7 days'
WHERE p1.commodity = %s
  AND p1.mandi = %s
  AND p1.price_date = %s;
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Model Registry Queries
# ═══════════════════════════════════════════════════════════════════════════════

REGISTER_MODEL = """
INSERT INTO model_registry (regime, version, r2_train, r2_val, mae_val, n_train, n_val,
                             artifact_path, feature_names, trained_at, is_active)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE);
"""

PROMOTE_MODEL = """
-- Atomically promote a model: deactivate old, activate new
BEGIN;
UPDATE model_registry SET is_active = FALSE WHERE regime = %s AND is_active = TRUE;
UPDATE model_registry SET is_active = TRUE WHERE id = %s;
COMMIT;
"""

ACTIVE_MODELS = """
SELECT regime, version, r2_val, mae_val, n_train, trained_at
FROM model_registry
WHERE is_active = TRUE
ORDER BY regime;
"""
