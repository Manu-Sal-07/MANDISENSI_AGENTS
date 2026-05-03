"""
Prediction Orchestrator — Production Coordination Layer.

Manages the full prediction lifecycle:
  1. Check Redis cache for recent results
  2. Run agents concurrently with timeout + retry
  3. Execute Phase-1.5 fusion
  4. Apply Phase-2.5 learned correction
  5. Log prediction to PostgreSQL (async, non-blocking)
  6. Cache result, return response

Design:
  • Agents run via asyncio.to_thread (CPU-bound work on thread pool)
  • External agent failure → graceful degradation (neutral defaults)
  • Redis unavailable → bypass cache, compute fresh
  • DB unavailable → fallback to JSONL logging
  • Learned model unavailable → pure Phase-1 fallback (α=1.0)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from utils.logger import get_logger
import monitoring.metrics as metrics

logger = get_logger(__name__)

# Cache TTL defaults (seconds)
_PREDICTION_CACHE_TTL = 3600   # 1 hour
_AGENT_TIMEOUT = 120.0         # seconds per agent (increased for first-time training)
_MAX_RETRIES = 1


class PredictionController:
    """
    Production orchestrator for the MandiSense prediction pipeline.

    Coordinates agent execution, ensemble fusion, caching, and logging
    in a single async-safe entry point.
    """

    def __init__(self, redis_client=None, db_client=None):
        """
        Args:
            redis_client: Optional aioredis/redis.asyncio client.
                          If None, caching is disabled (dev mode).
            db_client:    Optional AsyncDBClient for PostgreSQL logging.
                          If None, falls back to JSONL PredictionLogger.
        """
        self.redis = redis_client
        self.db = db_client
        self._learned_ensemble = None
        self._prediction_logger = None
        self._load_components()

    def _load_components(self):
        """Lazy-load ML components to avoid import-time side effects."""
        # JSONL fallback logger (used when DB is unavailable)
        try:
            from ensemble.prediction_logger import PredictionLogger
            self._prediction_logger = PredictionLogger()
        except Exception as e:
            logger.warning(f"PredictionLogger unavailable: {e}")

        try:
            from ensemble.learned_ensemble import LearnedEnsemble
            le = LearnedEnsemble()
            if le.load():
                self._learned_ensemble = le
                logger.info("LearnedEnsemble loaded successfully")
            else:
                logger.info("No trained models found — Phase-1 only mode")
        except Exception as e:
            logger.warning(f"LearnedEnsemble unavailable: {e}")

    # ─── Main Entry Point ─────────────────────────────────────────────

    async def predict(
        self,
        commodity: str,
        mandi: str,
        use_learned: bool = True,
    ) -> Dict[str, Any]:
        """
        Full prediction pipeline with caching, retries, and fallbacks.

        Returns a dict matching the PredictResponse schema.
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.monotonic()

        # 1. Check cache
        cache_key = f"pred:{commodity}:{mandi}"
        cached = await self._cache_get(cache_key)
        if cached:
            cached["metadata"]["cached"] = True
            cached["request_id"] = request_id
            return cached

        # 2. Run agents concurrently
        s_out, a_out, e_impact, e_conf = await self._run_agents(commodity, mandi)

        # 3. Phase-1.5 fusion (always runs)
        from ensemble.meta_ensemble import run_meta_ensemble
        phase1_result = run_meta_ensemble(
            seasonality_output=s_out,
            arrival_output=a_out,
            external_impact=e_impact,
            external_confidence=e_conf,
        )

        # 4. Phase-2.5 learned correction
        phase2_info = {
            "mode": "phase1_only",
            "alpha": 1.0,
            "regime_detected": "normal",
            "learned_residual": 0.0,
            "soft_regime_weights": None,
        }

        final_pred = phase1_result.final_prediction
        final_conf = phase1_result.final_confidence

        s_meta = s_out.metadata or {}
        a_meta = a_out.metadata or {}

        if use_learned and self._learned_ensemble and self._learned_ensemble.is_ready:
            try:
                blend = self._learned_ensemble.predict_and_blend(
                    seasonality_pred_30d=float(s_out.prediction),
                    seasonality_confidence=float(s_out.confidence),
                    seasonality_volatility=float(s_meta.get("return_std", 0)) / 100.0,
                    seasonality_regime=str(s_meta.get("cycle_phase", "neutral")),
                    arrival_pred_7d=float(a_out.prediction),
                    arrival_confidence=float(a_out.confidence),
                    arrival_supply_stress=float(a_meta.get("supply_stress_score", 0)),
                    arrival_regime=str(a_meta.get("supply_regime", "normal")),
                    external_impact=e_impact,
                    external_confidence=e_conf,
                    phase1_prediction=phase1_result.final_prediction,
                    phase1_confidence=phase1_result.final_confidence,
                )
                final_pred = blend["final_prediction"]
                final_conf = blend["final_confidence"]
                phase2_info = {
                    "mode": blend.get("mode", "blended"),
                    "alpha": blend.get("alpha", 1.0),
                    "regime_detected": blend.get("regime_detected", "normal"),
                    "learned_residual": blend.get("learned_residual", 0.0),
                    "soft_regime_weights": blend.get("soft_regime_weights"),
                }
            except Exception as e:
                logger.warning(f"[Orchestrator] Learned ensemble failed, using Phase-1: {e}")

        # 5. Build response
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        direction = "neutral"
        if final_pred > 2.0:
            direction = "bullish"
        elif final_pred < -2.0:
            direction = "bearish"

        # --- Farmer UI Mapping ---
        vol_pct = float(s_out.metadata.get("return_std", 2.0)) if s_out.metadata else 2.0
        threshold = -(0.5 * vol_pct)
        # Step 1: Scale threshold by 0.8 to increase SELL sensitivity by ~20-30%
        sell_threshold = 0.8 * threshold
        decision = "SELL" if final_pred < sell_threshold else "WAIT"

        # Step 2: Relaxed confidence gate from 0.2 → 0.15
        if final_conf < 0.15:
            decision = "WAIT"
        
        # Simple price range generation based on prediction
        # (In a real system, base_price comes from current mandi prices)
        base_price = 30  
        predicted_price = base_price * (1 + final_pred / 100.0)
        price_range = {
            "min": round(predicted_price * 0.95, 2),
            "max": round(predicted_price * 1.05, 2)
        }
        
        confidence_label = "High" if final_conf > 0.7 else ("Medium" if final_conf > 0.4 else "Low")
        
        # Risk label based on regimes and conflicts
        risk_label = "High" if phase1_result.risk_flags.get("strong_conflict") or phase2_info.get("regime_detected") == "shock" else ("Medium" if phase1_result.risk_flags.get("conflict_detected") else "Low")
        
        explanation = []
        if float(a_out.prediction) < -5.0:
            explanation.append("High arrival volume expected to drop prices")
        elif float(a_out.prediction) > 5.0:
            explanation.append("Supply shortage expected to increase prices")
        if float(s_out.prediction) > 2.0:
            explanation.append("Positive seasonal trend")
        elif float(s_out.prediction) < -2.0:
            explanation.append("Negative seasonal trend")
        
        if not explanation:
            explanation.append("Stable market conditions")

        farmer_guidance = {
            "decision": decision,
            "price_range": price_range,
            "confidence_label": confidence_label,
            "risk_label": risk_label,
            "explanation": explanation
        }

        result = {
            "request_id": request_id,
            "commodity": commodity,
            "mandi": mandi,
            "prediction": {
                "price_change_7d_pct": round(final_pred, 4),
                "confidence": round(final_conf, 4),
                "direction": direction,
            },
            "attribution": {
                k: round(v, 2) for k, v in phase1_result.attribution.items()
            },
            "risk_flags": phase1_result.risk_flags,
            "phase2_info": phase2_info,
            "farmer_guidance": farmer_guidance,
            "metadata": {
                "model_version": "v2.5.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "latency_ms": round(elapsed_ms, 1),
                "cached": False,
            },
        }

        # 6. Log prediction (async, non-blocking — fire-and-forget)
        asyncio.create_task(
            self._log_prediction_async(
                commodity, mandi, s_out, a_out,
                e_impact, e_conf, phase1_result,
                final_pred, final_conf, phase2_info,
            )
        )

        # 7. Cache result
        await self._cache_set(cache_key, result, ttl=_PREDICTION_CACHE_TTL)
        
        # 8. Record ML metrics
        metrics.record_prediction_metrics(
            commodity=commodity,
            mandi=mandi,
            blend_mode=phase2_info["mode"],
            confidence=final_conf,
            prediction=final_pred
        )

        logger.info(
            f"[Orchestrator] Prediction complete: {commodity}/{mandi} "
            f"pred={final_pred:.4f} conf={final_conf:.4f} "
            f"mode={phase2_info['mode']} latency={elapsed_ms:.0f}ms"
        )
        return result

    # ─── Agent Execution ──────────────────────────────────────────────

    async def _run_agents(self, commodity: str, mandi: str):
        """Run all agents concurrently with timeout and failure isolation."""
        from core.agents.seasonality_agent import run_seasonality_agent
        from core.agents.arrival_volume_agent import run_arrival_volume_agent
        from core.agents.external_factors_agent import run_external_factors_agent

        # Run Seasonality, Arrival, and External Factors in parallel
        results = await asyncio.gather(
            self._run_with_retry(run_seasonality_agent, commodity, mandi),
            self._run_with_retry(run_arrival_volume_agent, commodity, mandi),
            self._run_with_retry(run_external_factors_agent, commodity, mandi),
            return_exceptions=True,
        )

        s_out = results[0]
        a_out = results[1]
        e_out = results[2]

        if isinstance(s_out, Exception):
            raise RuntimeError(f"Seasonality agent failed after retries: {s_out}")
        if isinstance(a_out, Exception):
            raise RuntimeError(f"Arrival agent failed after retries: {a_out}")

        if isinstance(e_out, Exception):
            logger.warning(f"External Factors agent failed after retries: {e_out}")
            e_impact = 0.0
            e_conf = 0.0
        else:
            e_impact = float(e_out.get("impact_score", 0.0))
            e_conf = float(e_out.get("confidence", 0.0))

        return s_out, a_out, e_impact, e_conf

    async def _run_with_retry(self, fn, *args):
        """Run a sync function on the thread pool with retries."""
        last_exc = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(fn, *args),
                    timeout=_AGENT_TIMEOUT,
                )
            except Exception as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    wait = 1.0 * (attempt + 1)
                    logger.warning(
                        f"[Orchestrator] {fn.__name__} attempt {attempt+1} failed: {e}. "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
        raise last_exc

    # ─── Logging (Async DB → JSONL fallback) ──────────────────────────

    async def _log_prediction_async(
        self, commodity, mandi, s_out, a_out,
        e_impact, e_conf, phase1_result,
        final_pred, final_conf, phase2_info,
    ):
        """
        Log prediction to PostgreSQL asynchronously.
        Falls back to JSONL if DB is unavailable.
        """
        s_meta = s_out.metadata or {}
        a_meta = a_out.metadata or {}

        kwargs = dict(
            commodity=commodity,
            mandi=mandi,
            seasonality_pred_30d=float(s_out.prediction),
            seasonality_confidence=float(s_out.confidence),
            seasonality_volatility=float(s_meta.get("return_std", 0)) / 100.0,
            seasonality_regime=str(s_meta.get("cycle_phase", "neutral")),
            arrival_pred_7d=float(a_out.prediction),
            arrival_confidence=float(a_out.confidence),
            arrival_supply_stress=float(a_meta.get("supply_stress_score", 0)),
            arrival_regime=str(a_meta.get("supply_regime", "normal")),
            external_impact=e_impact,
            external_confidence=e_conf,
            phase1_prediction=phase1_result.final_prediction,
            phase1_confidence=phase1_result.final_confidence,
            phase1_conflict=phase1_result.risk_flags.get("conflict_detected", False),
            phase1_strong_conflict=phase1_result.risk_flags.get("strong_conflict", False),
            final_prediction=final_pred,
            final_confidence=final_conf,
            alpha=phase2_info.get("alpha"),
            learned_residual=phase2_info.get("learned_residual"),
            regime_detected=phase2_info.get("regime_detected"),
            blend_mode=phase2_info.get("mode"),
        )

        # Try async DB first
        if self.db and self.db.is_connected:
            try:
                await self.db.insert_prediction(**kwargs)
                return
            except Exception as e:
                logger.warning(f"[Orchestrator] Async DB log failed: {e}")

        # Fallback to sync JSONL
        if self._prediction_logger:
            try:
                # JSONL logger doesn't have the Phase-2.5 fields, extract base fields
                self._prediction_logger.log_prediction(
                    commodity=kwargs["commodity"],
                    mandi=kwargs["mandi"],
                    seasonality_pred_30d=kwargs["seasonality_pred_30d"],
                    seasonality_confidence=kwargs["seasonality_confidence"],
                    seasonality_volatility=kwargs["seasonality_volatility"],
                    seasonality_regime=kwargs["seasonality_regime"],
                    arrival_pred_7d=kwargs["arrival_pred_7d"],
                    arrival_confidence=kwargs["arrival_confidence"],
                    arrival_supply_stress=kwargs["arrival_supply_stress"],
                    arrival_regime=kwargs["arrival_regime"],
                    external_impact=kwargs["external_impact"],
                    external_confidence=kwargs["external_confidence"],
                    phase1_prediction=kwargs["phase1_prediction"],
                    phase1_confidence=kwargs["phase1_confidence"],
                    phase1_conflict=kwargs["phase1_conflict"],
                    phase1_strong_conflict=kwargs["phase1_strong_conflict"],
                )
            except Exception as e:
                logger.warning(f"[Orchestrator] JSONL fallback also failed: {e}")

    # ─── Cache Helpers ────────────────────────────────────────────────

    async def _cache_get(self, key: str) -> Optional[Dict]:
        if not self.redis:
            return None
        try:
            raw = await self.redis.get(key)
            if raw:
                metrics.CACHE_OPERATIONS_TOTAL.labels(operation="get", status="hit").inc()
                return json.loads(raw)
            else:
                metrics.CACHE_OPERATIONS_TOTAL.labels(operation="get", status="miss").inc()
                return None
        except Exception:
            metrics.CACHE_OPERATIONS_TOTAL.labels(operation="get", status="error").inc()
            return None

    async def _cache_set(self, key: str, value: Dict, ttl: int = 3600):
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
            metrics.CACHE_OPERATIONS_TOTAL.labels(operation="set", status="ok").inc()
        except Exception:
            metrics.CACHE_OPERATIONS_TOTAL.labels(operation="set", status="error").inc()
            pass

    async def invalidate_cache(self, commodity: str, mandi: str):
        """Called after new data ingestion to force fresh predictions."""
        if not self.redis:
            return
        try:
            key = f"pred:{commodity}:{mandi}"
            await self.redis.delete(key)
        except Exception:
            pass


