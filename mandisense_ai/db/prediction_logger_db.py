"""
Database Prediction Logger — PostgreSQL-backed replacement for JSONL logging.

Drop-in replacement for PredictionLogger. Provides the EXACT SAME public API
so the orchestrator and training pipeline require zero changes.

API Compatibility:
  • log_prediction(...)  → INSERT into prediction_log
  • backfill_actual(...) → UPDATE prediction_log SET actual_7d_change = ...
  • read_all()           → SELECT * FROM prediction_log
  • read_completed(...)  → SELECT * WHERE actual_7d_change IS NOT NULL
  • count_records(...)   → SELECT COUNT(*)

Design:
  • Uses sync psycopg2 pool (same as original JSONL logger — sync callers)
  • Falls back to JSONL if database is unavailable (safety net)
  • Parameterized queries (SQL injection safe)
  • Idempotent: duplicate record_ids are caught by UNIQUE constraint
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class DatabasePredictionLogger:
    """PostgreSQL-backed prediction logger with JSONL fallback."""

    def __init__(self, fallback_dir: Optional[Path] = None):
        """
        Args:
            fallback_dir: If set, JSONL fallback writes go here when DB is down.
        """
        self._pool = None
        self._fallback_dir = Path(fallback_dir) if fallback_dir else Path("data/ensemble")
        self._init_pool()

    def _init_pool(self):
        try:
            from db.connection import get_sync_pool
            self._pool = get_sync_pool()
            if self._pool:
                logger.info("[DBLogger] Connected to PostgreSQL")
        except Exception as e:
            logger.warning(f"[DBLogger] DB unavailable, using JSONL fallback: {e}")

    def _get_conn(self):
        if self._pool is None:
            return None
        try:
            return self._pool.getconn()
        except Exception:
            return None

    def _put_conn(self, conn):
        if self._pool and conn:
            self._pool.putconn(conn)

    # ─── Write ────────────────────────────────────────────────────────

    def log_prediction(
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
        phase1_conflict: bool,
        phase1_strong_conflict: bool,
    ) -> str:
        """Insert a prediction record. Returns the record_id (UUID)."""
        record_id = str(uuid.uuid4())
        now = datetime.utcnow()

        conn = self._get_conn()
        if conn is None:
            return self._fallback_log(record_id, now, locals())

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO prediction_log (
                        record_id, created_at, commodity, mandi,
                        seasonality_pred_30d, seasonality_confidence,
                        seasonality_volatility, seasonality_regime,
                        arrival_pred_7d, arrival_confidence,
                        arrival_supply_stress, arrival_regime,
                        external_impact, external_confidence,
                        phase1_prediction, phase1_confidence,
                        phase1_conflict, phase1_strong_conflict
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    )
                """, (
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
                ))
            conn.commit()
            logger.info(f"[DBLogger] Logged {record_id} for {commodity}/{mandi}")
        except Exception as e:
            conn.rollback()
            logger.warning(f"[DBLogger] INSERT failed, using fallback: {e}")
            return self._fallback_log(record_id, now, locals())
        finally:
            self._put_conn(conn)

        return record_id

    # ─── Backfill ─────────────────────────────────────────────────────

    def backfill_actual(
        self,
        commodity: str,
        mandi: str,
        target_timestamp: str,
        actual_7d_change: float,
    ) -> int:
        """
        Backfill actual outcome for matching unfilled records.
        Returns count of records updated.
        """
        target_date = target_timestamp[:10]

        conn = self._get_conn()
        if conn is None:
            return 0

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE prediction_log
                    SET actual_7d_change = %s,
                        outcome_filled_at = NOW()
                    WHERE commodity = %s
                      AND mandi = %s
                      AND created_at::date = %s::date
                      AND actual_7d_change IS NULL
                """, (
                    round(float(actual_7d_change), 6),
                    commodity,
                    mandi,
                    target_date,
                ))
                updated = cur.rowcount
            conn.commit()
            if updated > 0:
                logger.info(f"[DBLogger] Backfilled {updated} records for {commodity}/{mandi} on {target_date}")
            return updated
        except Exception as e:
            conn.rollback()
            logger.warning(f"[DBLogger] Backfill failed: {e}")
            return 0
        finally:
            self._put_conn(conn)

    # ─── Read ─────────────────────────────────────────────────────────

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all records from prediction_log."""
        conn = self._get_conn()
        if conn is None:
            return []

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT record_id, created_at, commodity, mandi,
                           seasonality_pred_30d, seasonality_confidence,
                           seasonality_volatility, seasonality_regime,
                           arrival_pred_7d, arrival_confidence,
                           arrival_supply_stress, arrival_regime,
                           external_impact, external_confidence,
                           phase1_prediction, phase1_confidence,
                           phase1_conflict, phase1_strong_conflict,
                           actual_7d_change, outcome_filled_at
                    FROM prediction_log
                    ORDER BY created_at ASC
                """)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            return [self._row_to_dict(columns, row) for row in rows]
        except Exception as e:
            logger.warning(f"[DBLogger] read_all failed: {e}")
            return []
        finally:
            self._put_conn(conn)

    def read_completed(
        self,
        commodity: Optional[str] = None,
        mandi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read records with backfilled actuals (training-eligible)."""
        conn = self._get_conn()
        if conn is None:
            return []

        try:
            query = """
                SELECT record_id, created_at, commodity, mandi,
                       seasonality_pred_30d, seasonality_confidence,
                       seasonality_volatility, seasonality_regime,
                       arrival_pred_7d, arrival_confidence,
                       arrival_supply_stress, arrival_regime,
                       external_impact, external_confidence,
                       phase1_prediction, phase1_confidence,
                       phase1_conflict, phase1_strong_conflict,
                       actual_7d_change, outcome_filled_at
                FROM prediction_log
                WHERE actual_7d_change IS NOT NULL
            """
            params = []

            if commodity:
                query += " AND commodity = %s"
                params.append(commodity)
            if mandi:
                query += " AND mandi = %s"
                params.append(mandi)

            query += " ORDER BY created_at ASC"

            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            return [self._row_to_dict(columns, row) for row in rows]
        except Exception as e:
            logger.warning(f"[DBLogger] read_completed failed: {e}")
            return []
        finally:
            self._put_conn(conn)

    def count_records(
        self,
        commodity: Optional[str] = None,
        mandi: Optional[str] = None,
        completed_only: bool = False,
    ) -> int:
        """Count records with optional filters."""
        conn = self._get_conn()
        if conn is None:
            return 0

        try:
            query = "SELECT COUNT(*) FROM prediction_log WHERE 1=1"
            params = []

            if completed_only:
                query += " AND actual_7d_change IS NOT NULL"
            if commodity:
                query += " AND commodity = %s"
                params.append(commodity)
            if mandi:
                query += " AND mandi = %s"
                params.append(mandi)

            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.fetchone()[0]
        except Exception as e:
            logger.warning(f"[DBLogger] count_records failed: {e}")
            return 0
        finally:
            self._put_conn(conn)

    # ─── Helpers ──────────────────────────────────────────────────────

    def _row_to_dict(self, columns: list, row: tuple) -> Dict[str, Any]:
        """Convert a DB row to a dict matching the JSONL schema."""
        d = dict(zip(columns, row))
        # Normalize types for downstream compatibility
        d["timestamp"] = d.pop("created_at").isoformat() + "Z" if d.get("created_at") else ""
        d["record_id"] = str(d.get("record_id", ""))

        # Convert Decimal types to float
        for key in d:
            if hasattr(d[key], "is_finite"):  # Decimal check
                d[key] = float(d[key])

        return d

    def _fallback_log(self, record_id: str, now: datetime, local_vars: dict) -> str:
        """Write to JSONL file when DB is unavailable."""
        self._fallback_dir.mkdir(parents=True, exist_ok=True)
        path = self._fallback_dir / "meta_predictions.jsonl"

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

        logger.info(f"[DBLogger] Fallback: wrote {record_id} to {path}")
        return record_id
