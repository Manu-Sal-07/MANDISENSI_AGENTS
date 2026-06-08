"""
Prediction Logger — Phase 2 Append-Only Logging Pipeline.

Logs every meta-ensemble prediction cycle to disk for later use
by the learned ensemble.  Records are written in append-only JSONL
format with no in-place mutation (actuals are backfilled via a
separate update pass).

Design:
  • Append-only writes — safe for concurrent runners
  • JSONL format — one JSON object per line, streamable
  • Actual outcomes start as null, backfilled after horizon elapses
  • No data leakage — records only become training-eligible once
    actual outcomes are populated
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Default storage path (relative to working directory)
_DEFAULT_LOG_DIR = Path("data") / "ensemble"
_DEFAULT_LOG_FILE = "meta_predictions.jsonl"


class PredictionLogger:
    """Append-only logger for meta-ensemble prediction records."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else _DEFAULT_LOG_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / _DEFAULT_LOG_FILE

    # ─── Write ────────────────────────────────────────────────────────

    def log_prediction(
        self,
        commodity: str,
        mandi: str,
        # Seasonality inputs
        seasonality_pred_30d: float,
        seasonality_confidence: float,
        seasonality_volatility: float,
        seasonality_regime: str,
        # Arrival inputs
        arrival_pred_7d: float,
        arrival_confidence: float,
        arrival_supply_stress: float,
        arrival_regime: str,
        # External inputs
        external_impact: float,
        external_confidence: float,
        # Phase-1 outputs
        phase1_prediction: float,
        phase1_confidence: float,
        phase1_conflict: bool,
        phase1_strong_conflict: bool,
    ) -> str:
        """
        Append one prediction record.  Returns the generated record_id.

        actual_7d_change is always null at log time — it must be
        backfilled later via ``backfill_actual()``.
        """
        record_id = str(uuid.uuid4())
        record = {
            "record_id": record_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "commodity": commodity,
            "mandi": mandi,
            # Seasonality
            "seasonality_pred_30d": round(float(seasonality_pred_30d), 6),
            "seasonality_confidence": round(float(seasonality_confidence), 4),
            "seasonality_volatility": round(float(seasonality_volatility), 4),
            "seasonality_regime": str(seasonality_regime),
            # Arrival
            "arrival_pred_7d": round(float(arrival_pred_7d), 6),
            "arrival_confidence": round(float(arrival_confidence), 4),
            "arrival_supply_stress": round(float(arrival_supply_stress), 4),
            "arrival_regime": str(arrival_regime),
            # External
            "external_impact": round(float(external_impact), 4),
            "external_confidence": round(float(external_confidence), 4),
            # Phase-1 output
            "phase1_prediction": round(float(phase1_prediction), 6),
            "phase1_confidence": round(float(phase1_confidence), 4),
            "phase1_conflict": bool(phase1_conflict),
            "phase1_strong_conflict": bool(phase1_strong_conflict),
            # Outcome (backfilled later)
            "actual_7d_change": None,
            "outcome_filled_at": None,
        }

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(
            f"[PredictionLogger] Logged record {record_id} "
            f"for {commodity}/{mandi}"
        )
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

        Matches on commodity + mandi + timestamp prefix (date).
        Returns count of records updated.

        Note: This reads and rewrites the entire file.  For production
        at scale, migrate to SQLite or append a separate outcomes file.
        """
        if not self.file_path.exists():
            return 0

        target_date = target_timestamp[:10]  # YYYY-MM-DD prefix
        updated = 0
        records: List[Dict[str, Any]] = []

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if (
                    record.get("commodity") == commodity
                    and record.get("mandi") == mandi
                    and record.get("timestamp", "")[:10] == target_date
                    and record.get("actual_7d_change") is None
                ):
                    record["actual_7d_change"] = round(float(actual_7d_change), 6)
                    record["outcome_filled_at"] = datetime.utcnow().isoformat() + "Z"
                    updated += 1
                records.append(record)

        with open(self.file_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        if updated > 0:
            logger.info(
                f"[PredictionLogger] Backfilled {updated} records "
                f"for {commodity}/{mandi} on {target_date}"
            )
        return updated

    # ─── Read ─────────────────────────────────────────────────────────

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all records from the log file."""
        if not self.file_path.exists():
            return []
        records = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("[PredictionLogger] Skipping malformed line")
        return records

    def read_completed(
        self,
        commodity: Optional[str] = None,
        mandi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read only records where actual outcome has been filled.
        These are the only records eligible for training.
        """
        records = self.read_all()
        completed = [
            r for r in records
            if r.get("actual_7d_change") is not None
        ]
        if commodity:
            completed = [r for r in completed if r.get("commodity") == commodity]
        if mandi:
            completed = [r for r in completed if r.get("mandi") == mandi]
        return completed

    def count_records(
        self,
        commodity: Optional[str] = None,
        mandi: Optional[str] = None,
        completed_only: bool = False,
    ) -> int:
        """Count records, optionally filtering by commodity/mandi."""
        if completed_only:
            return len(self.read_completed(commodity, mandi))
        records = self.read_all()
        if commodity:
            records = [r for r in records if r.get("commodity") == commodity]
        if mandi:
            records = [r for r in records if r.get("mandi") == mandi]
        return len(records)
