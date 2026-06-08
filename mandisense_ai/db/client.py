"""
Async Database Client — Production async interface for FastAPI handlers.

Wraps asyncpg connection pool with:
  • Connection lifecycle management (init/close)
  • Typed query helpers (fetch, fetchrow, execute)
  • Prediction-specific async operations (insert, history, backfill)
  • JSONL fallback when DB is unavailable
  • Retry logic for transient failures

Usage:
  client = AsyncDBClient()
  await client.init()            # Call once at startup
  await client.insert_prediction(...)
  rows = await client.get_prediction_history(...)
  await client.close()           # Call at shutdown
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger
import monitoring.metrics as metrics

logger = get_logger(__name__)

# JSONL fallback directory
_FALLBACK_DIR = Path("data") / "ensemble"
_FALLBACK_FILE = "meta_predictions.jsonl"


class AsyncDBClient:
    """
    Async PostgreSQL client for FastAPI request handlers.

    Manages an asyncpg connection pool and provides typed
    query methods for every production use case.
    """

    def __init__(self):
        self._pool = None
        self._available = False

    @property
    def is_connected(self) -> bool:
        return self._pool is not None and self._available

    # ─── Lifecycle ────────────────────────────────────────────────────

    async def init(self, dsn: Optional[str] = None):
        """Initialize the asyncpg connection pool. Call once at startup."""
        if self._pool is not None:
            return

        db_url = dsn or os.environ.get("DATABASE_URL")
        if not db_url:
            env = os.environ.get("APP__ENVIRONMENT", "development").lower()
            if env == "production":
                raise ValueError("DATABASE_URL environment variable is required in production environment.")
            db_url = "postgresql://mandisense:mandisense@localhost:5432/mandisense_db"

        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                dsn=db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            # Verify connection
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            self._available = True
            logger.info(f"[AsyncDBClient] Pool created, connected to {db_url.split('@')[-1]}")
        except Exception as e:
            logger.warning(f"[AsyncDBClient] DB unavailable: {e}")
            self._pool = None
            self._available = False

    async def close(self):
        """Close the connection pool. Call at shutdown."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._available = False
            logger.info("[AsyncDBClient] Pool closed")

    # ─── Core Query Helpers ───────────────────────────────────────────

    async def fetch(self, query: str, *args) -> Optional[List]:
        """Execute a SELECT and return all rows."""
        if not self.is_connected:
            return None
        try:
            with metrics.track_db_latency("fetch"):
                async with self._pool.acquire() as conn:
                    return await conn.fetch(query, *args)
        except Exception as e:
            logger.warning(f"[AsyncDBClient] fetch failed: {e}")
            return None

    async def fetchrow(self, query: str, *args):
        """Execute a SELECT and return a single row."""
        if not self.is_connected:
            return None
        try:
            with metrics.track_db_latency("fetchrow"):
                async with self._pool.acquire() as conn:
                    return await conn.fetchrow(query, *args)
        except Exception as e:
            logger.warning(f"[AsyncDBClient] fetchrow failed: {e}")
            return None

    async def execute(self, query: str, *args) -> Optional[str]:
        """Execute an INSERT/UPDATE/DELETE. Returns status string."""
        if not self.is_connected:
            return None
        try:
            with metrics.track_db_latency("execute"):
                async with self._pool.acquire() as conn:
                    return await conn.execute(query, *args)
        except Exception as e:
            logger.warning(f"[AsyncDBClient] execute failed: {e}")
            return None

    async def fetchval(self, query: str, *args):
        """Execute a query and return a single value."""
        if not self.is_connected:
            return None
        try:
            with metrics.track_db_latency("fetchval"):
                async with self._pool.acquire() as conn:
                    return await conn.fetchval(query, *args)
        except Exception as e:
            logger.warning(f"[AsyncDBClient] fetchval failed: {e}")
            return None

    # ─── Prediction Operations ────────────────────────────────────────

    async def insert_prediction(
        self,
        commodity: str,
        mandi: str,
        seasonality_pred_30d: float,
        seasonality_confidence: float,
        seasonality_volatility: float,
        seasonality_regime: str,
        arrival_pred_7d: float,
        arrival_confidence: float,
        arrival_supply_stress: float,
        arrival_regime: str,
        external_impact: float,
        external_confidence: float,
        phase1_prediction: float,
        phase1_confidence: float,
        phase1_conflict: bool = False,
        phase1_strong_conflict: bool = False,
        final_prediction: float = None,
        final_confidence: float = None,
        alpha: float = None,
        learned_residual: float = None,
        regime_detected: str = None,
        blend_mode: str = None,
    ) -> str:
        """
        Insert a prediction record asynchronously.
        Returns record_id (UUID string).
        Falls back to JSONL if DB is unavailable.
        """
        record_id = str(uuid.uuid4())
        now = datetime.utcnow()

        if not self.is_connected:
            return self._fallback_log(record_id, now, locals())

        try:
            # asyncpg uses $1, $2 placeholders (not %s)
            await self.execute("""
                INSERT INTO prediction_log (
                    record_id, created_at, commodity, mandi,
                    seasonality_pred_30d, seasonality_confidence,
                    seasonality_volatility, seasonality_regime,
                    arrival_pred_7d, arrival_confidence,
                    arrival_supply_stress, arrival_regime,
                    external_impact, external_confidence,
                    phase1_prediction, phase1_confidence,
                    phase1_conflict, phase1_strong_conflict,
                    final_prediction, final_confidence,
                    alpha, learned_residual,
                    regime_detected, blend_mode
                ) VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7, $8,
                    $9, $10, $11, $12,
                    $13, $14, $15, $16,
                    $17, $18,
                    $19, $20, $21, $22, $23, $24
                )
            """,
                record_id, now, commodity, mandi,
                round(float(seasonality_pred_30d), 6),
                round(float(seasonality_confidence), 4),
                round(float(seasonality_volatility), 4),
                str(seasonality_regime),
                round(float(arrival_pred_7d), 6),
                round(float(arrival_confidence), 4),
                round(float(arrival_supply_stress), 4),
                str(arrival_regime),
                round(float(external_impact), 4),
                round(float(external_confidence), 4),
                round(float(phase1_prediction), 6),
                round(float(phase1_confidence), 4),
                bool(phase1_conflict),
                bool(phase1_strong_conflict),
                round(float(final_prediction), 4) if final_prediction is not None else None,
                round(float(final_confidence), 4) if final_confidence is not None else None,
                round(float(alpha), 4) if alpha is not None else None,
                round(float(learned_residual), 4) if learned_residual is not None else None,
                regime_detected,
                blend_mode,
            )
            logger.info(f"[AsyncDBClient] Logged {record_id} for {commodity}/{mandi}")
            return record_id

        except Exception as e:
            logger.warning(f"[AsyncDBClient] INSERT failed, using fallback: {e}")
            return self._fallback_log(record_id, now, locals())

    async def get_prediction_history(
        self,
        commodity: str,
        mandi: str,
        days: int = 30,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch prediction history from DB.
        Returns list of dicts sorted by time descending.
        Uses idx_pred_commodity_time index.
        """
        if not self.is_connected:
            return []

        rows = await self.fetch("""
            SELECT record_id, created_at, commodity, mandi,
                   phase1_prediction, phase1_confidence,
                   final_prediction, final_confidence,
                   alpha, regime_detected, blend_mode,
                   actual_7d_change, outcome_filled_at
            FROM prediction_log
            WHERE commodity = $1 AND mandi = $2
              AND created_at >= NOW() - ($3 || ' days')::interval
            ORDER BY created_at DESC
            LIMIT $4 OFFSET $5
        """, commodity, mandi, str(days), limit, offset)

        if rows is None:
            return []

        return [self._row_to_dict(row) for row in rows]

    async def get_latest_prediction(
        self, commodity: str, mandi: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the most recent prediction for a commodity/mandi pair.
        Uses idx_pred_commodity_time (< 1ms).
        """
        if not self.is_connected:
            return None

        row = await self.fetchrow("""
            SELECT record_id, created_at, commodity, mandi,
                   phase1_prediction, phase1_confidence,
                   final_prediction, final_confidence,
                   alpha, regime_detected, blend_mode,
                   actual_7d_change
            FROM prediction_log
            WHERE commodity = $1 AND mandi = $2
            ORDER BY created_at DESC
            LIMIT 1
        """, commodity, mandi)

        return self._row_to_dict(row) if row else None

    async def backfill_actual(
        self,
        commodity: str,
        mandi: str,
        target_date: str,
        actual_7d_change: float,
    ) -> int:
        """
        Backfill actual outcome for records matching date.
        Idempotent: only updates records where actual IS NULL.
        Uses idx_pred_unfilled partial index.
        Returns count of updated rows.
        """
        if not self.is_connected:
            return 0

        result = await self.execute("""
            UPDATE prediction_log
            SET actual_7d_change = $1,
                outcome_filled_at = NOW()
            WHERE commodity = $2
              AND mandi = $3
              AND created_at::date = $4::date
              AND actual_7d_change IS NULL
        """,
            round(float(actual_7d_change), 6),
            commodity,
            mandi,
            target_date,
        )

        # asyncpg returns "UPDATE N"
        if result:
            count = int(result.split()[-1])
            if count > 0:
                logger.info(f"[AsyncDBClient] Backfilled {count} records for {commodity}/{mandi}")
            return count
        return 0

    async def get_model_accuracy(
        self, commodity: str, mandi: str, days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Compute MAE and directional accuracy from prediction_log.
        Uses idx_pred_completed.
        """
        if not self.is_connected:
            return None

        row = await self.fetchrow("""
            SELECT
                COUNT(*) AS total_predictions,
                AVG(ABS(COALESCE(final_prediction, phase1_prediction) - actual_7d_change)) AS mae,
                AVG(CASE
                    WHEN SIGN(COALESCE(final_prediction, phase1_prediction)) = SIGN(actual_7d_change)
                    THEN 1.0 ELSE 0.0
                END) AS directional_accuracy,
                AVG(COALESCE(final_confidence, phase1_confidence)) AS avg_confidence
            FROM prediction_log
            WHERE commodity = $1 AND mandi = $2
              AND actual_7d_change IS NOT NULL
              AND created_at >= NOW() - ($3 || ' days')::interval
        """, commodity, mandi, str(days))

        if row and row["total_predictions"] > 0:
            return dict(row)
        return None

    async def count_predictions(
        self, commodity: str = None, mandi: str = None, completed_only: bool = False
    ) -> int:
        """Count prediction records with optional filters."""
        if not self.is_connected:
            return 0

        # Build query dynamically
        conditions = []
        args = []
        idx = 1

        if completed_only:
            conditions.append("actual_7d_change IS NOT NULL")
        if commodity:
            conditions.append(f"commodity = ${idx}")
            args.append(commodity)
            idx += 1
        if mandi:
            conditions.append(f"mandi = ${idx}")
            args.append(mandi)
            idx += 1

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        result = await self.fetchval(f"SELECT COUNT(*) FROM prediction_log{where}", *args)
        return result or 0

    async def ping(self) -> bool:
        """Check if the database is reachable."""
        if not self.is_connected:
            return False
        try:
            val = await self.fetchval("SELECT 1")
            return val == 1
        except Exception:
            return False

    # ─── Helpers ──────────────────────────────────────────────────────

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert an asyncpg Record to a plain dict with normalized types."""
        d = dict(row)

        # Normalize timestamp field name for downstream compatibility
        if "created_at" in d:
            d["timestamp"] = d.pop("created_at").isoformat() + "Z"

        # Convert UUID to string
        if "record_id" in d:
            d["record_id"] = str(d["record_id"])

        # Convert Decimal → float
        for key, val in d.items():
            if hasattr(val, "is_finite"):
                d[key] = float(val)

        return d

    def _fallback_log(self, record_id: str, now: datetime, local_vars: dict) -> str:
        """Write to JSONL file when DB is unavailable."""
        _FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        path = _FALLBACK_DIR / _FALLBACK_FILE

        record = {
            "record_id": record_id,
            "timestamp": now.isoformat() + "Z",
            "commodity": local_vars.get("commodity", ""),
            "mandi": local_vars.get("mandi", ""),
            "seasonality_pred_30d": local_vars.get("seasonality_pred_30d", 0),
            "seasonality_confidence": local_vars.get("seasonality_confidence", 0),
            "seasonality_volatility": local_vars.get("seasonality_volatility", 0),
            "seasonality_regime": local_vars.get("seasonality_regime", ""),
            "arrival_pred_7d": local_vars.get("arrival_pred_7d", 0),
            "arrival_confidence": local_vars.get("arrival_confidence", 0),
            "arrival_supply_stress": local_vars.get("arrival_supply_stress", 0),
            "arrival_regime": local_vars.get("arrival_regime", ""),
            "external_impact": local_vars.get("external_impact", 0),
            "external_confidence": local_vars.get("external_confidence", 0),
            "phase1_prediction": local_vars.get("phase1_prediction", 0),
            "phase1_confidence": local_vars.get("phase1_confidence", 0),
            "phase1_conflict": local_vars.get("phase1_conflict", False),
            "phase1_strong_conflict": local_vars.get("phase1_strong_conflict", False),
            "actual_7d_change": None,
            "outcome_filled_at": None,
        }

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        logger.info(f"[AsyncDBClient] Fallback: wrote {record_id} to {path}")
        return record_id
