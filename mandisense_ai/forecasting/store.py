"""
Storage layer for observations and published forecasts.

Two stores, deliberately separate:

* **ObservationStore** — append-only ground truth. One row per
  (date, commodity, mandi). Upserts are idempotent so re-running a night's
  job, or backfilling an overlapping range, can never duplicate or double
  count. This is the only thing the rest of the system treats as "what the
  market actually did".

* **ForecastStore** — the published output the API serves. Rewritten wholesale
  each run and swapped atomically, so a reader can never observe a half
  written table.

Parquet is used for observations (columnar, typed, compresses a long daily
series well) and JSON for the forecast table (small, human-inspectable, and
read by the API on every cold start).
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from mandisense_ai.forecasting.config import (
    forecast_store_path,
    ingestion_log_path,
    observations_path,
)
from mandisense_ai.utils.exceptions import StoreLockTimeoutError
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

OBSERVATION_COLUMNS = [
    "date",
    "commodity",
    "mandi_id",
    "modal_price",
    "min_price",
    "max_price",
    "arrivals",
    "state",
    "district",
    "source",
    "ingested_at",
    # Graded ingest-time confidence in the row (see `quality.py`). Carried on
    # the observation rather than recomputed downstream, because the signals
    # it is built from — the same-day peer cross-section above all — are only
    # available at the moment of ingestion.
    "quality_score",
    "quality_flags",
]

# Rows written before quality scoring existed carry no score. Treating them as
# fully trusted preserves the previous behaviour exactly, so introducing the
# column cannot silently reweight a decade of archive.
LEGACY_QUALITY_SCORE = 1.0

# (date, commodity, mandi_id) uniquely identifies an observation.
PRIMARY_KEY = ["date", "commodity", "mandi_id"]

FORECAST_SCHEMA_VERSION = "1.0.0"


@contextmanager
def _exclusive_lock(target: Path, wait_timeout: float = 30.0, stale_after: float = 1200.0):
    """
    Cross-platform advisory lock around a read-modify-write.

    Upsert reads the whole store, merges, and rewrites it. Two jobs doing that
    concurrently — a scheduled run overlapping a manual one — would have the
    second silently overwrite the first's inserts. An exclusive lock file makes
    that a wait instead of a data loss.

    `wait_timeout` and `stale_after` used to be the same number, and that was
    the bug: at 30 seconds, any legitimately running job that simply took
    longer than that — a real retrain measured on this project's own archive
    takes 30-40 seconds — would have its lock deleted and stolen out from
    under it by the next caller, the exact data race this function exists to
    prevent. The two are now separate. `wait_timeout` is how long a caller
    patiently polls before giving up. `stale_after` is how old the *lock
    itself* has to be, judged from the timestamp its actual holder recorded
    at acquisition, before it is presumed abandoned by a crashed process — set
    far above any real run duration. A lock that is merely being waited on
    longer than expected now raises rather than being silently broken; only a
    lock old enough to be abandoned is ever removed out from under its holder.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait_timeout
    handle = None

    while True:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(
                handle,
                json.dumps({"pid": os.getpid(), "acquired_at": time.time()}).encode("utf-8"),
            )
            break
        except FileExistsError:
            age = _lock_age_seconds(lock_path)
            if age is not None and age > stale_after:
                logger.warning(
                    "Lock at %s is %.0fs old (> stale_after=%.0fs) — treating as "
                    "abandoned by a crashed run and reclaiming it",
                    lock_path, age, stale_after,
                )
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue

            if time.time() > deadline:
                raise StoreLockTimeoutError(
                    f"Could not acquire lock at {lock_path} within {wait_timeout}s; "
                    f"holder is {age:.0f}s old, which is not yet past stale_after="
                    f"{stale_after}s. Refusing to write unprotected."
                    if age is not None
                    else f"Could not acquire lock at {lock_path} within {wait_timeout}s."
                )
            time.sleep(0.2)

    try:
        yield
    finally:
        if handle is not None:
            os.close(handle)
        try:
            lock_path.unlink()
        except OSError:
            pass


def _lock_age_seconds(lock_path: Path) -> Optional[float]:
    """Seconds since the current holder recorded acquiring this lock.

    Falls back to file mtime if the content is unreadable (an older-format
    lock, or a partial write caught mid-creation), so a corrupt lock file
    still ages out eventually instead of blocking forever.
    """
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        return time.time() - float(payload["acquired_at"])
    except Exception:
        try:
            return time.time() - lock_path.stat().st_mtime
        except OSError:
            return None


class ObservationStore:
    """Append-only, idempotent store of daily market observations."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else observations_path()

    # ------------------------------------------------------------- reading

    def read(self) -> pd.DataFrame:
        """Load the full store, or an empty typed frame if it does not exist."""
        if not self.path.exists():
            return pd.DataFrame(columns=OBSERVATION_COLUMNS)
        try:
            frame = pd.read_parquet(self.path, engine="pyarrow")
        except Exception as exc:  # pragma: no cover - corrupt file guard
            logger.error("Observation store unreadable at %s: %s", self.path, exc)
            return pd.DataFrame(columns=OBSERVATION_COLUMNS)
        frame["date"] = pd.to_datetime(frame["date"])
        if "quality_score" not in frame.columns:
            frame["quality_score"] = LEGACY_QUALITY_SCORE
        else:
            frame["quality_score"] = pd.to_numeric(
                frame["quality_score"], errors="coerce"
            ).fillna(LEGACY_QUALITY_SCORE)
        if "quality_flags" not in frame.columns:
            frame["quality_flags"] = ""
        return frame

    def lineage_hash(self, frame: Optional[pd.DataFrame] = None) -> str:
        """
        Content hash of the exact observation set.

        Recorded on every artifact built from this store so a published
        forecast can be traced to a byte-identical input, rather than to "the
        data as it was that night", which is not a thing anyone can reproduce.
        """
        import hashlib

        data = self.read() if frame is None else frame
        if data.empty:
            return "empty"
        keys = (
            data[PRIMARY_KEY + ["modal_price"]]
            .astype(str)
            .agg("|".join, axis=1)
            .sort_values()
        )
        digest = hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()
        return digest[:16]

    def read_series(self, commodity: str, mandi_id: str, limit: Optional[int] = None) -> pd.DataFrame:
        frame = self.read()
        if frame.empty:
            return frame
        subset = frame[
            (frame["commodity"] == commodity) & (frame["mandi_id"] == mandi_id)
        ].sort_values("date")
        return subset.tail(limit) if limit else subset

    def coverage(self) -> pd.DataFrame:
        """Per-series row counts and date bounds — the freshness dashboard."""
        frame = self.read()
        if frame.empty:
            return pd.DataFrame(columns=["commodity", "mandi_id", "rows", "first", "last"])
        grouped = (
            frame.groupby(["commodity", "mandi_id"])["date"]
            .agg(rows="count", first="min", last="max")
            .reset_index()
        )
        return grouped.sort_values(["commodity", "mandi_id"])

    # ------------------------------------------------------------- writing

    def upsert(self, records: pd.DataFrame) -> Dict[str, int]:
        """
        Merge new observations into the store.

        Existing rows for the same (date, commodity, mandi) are *replaced* by
        the incoming values — the upstream feed occasionally revises a day's
        print, and the later read is the better one. Returns counts so the
        caller can log exactly what a run changed.
        """
        if records is None or records.empty:
            return {"received": 0, "inserted": 0, "updated": 0, "total": len(self.read())}

        with _exclusive_lock(self.path):
            return self._upsert_locked(records)

    def _upsert_locked(self, records: pd.DataFrame) -> Dict[str, int]:
        incoming = self._conform(records)
        existing = self.read()

        if existing.empty:
            merged = incoming
            inserted, updated = len(incoming), 0
        else:
            existing_keys = set(
                map(tuple, existing[PRIMARY_KEY].astype(str).to_numpy().tolist())
            )
            incoming_keys = list(
                map(tuple, incoming[PRIMARY_KEY].astype(str).to_numpy().tolist())
            )
            updated = sum(1 for key in incoming_keys if key in existing_keys)
            inserted = len(incoming_keys) - updated

            merged = pd.concat([existing, incoming], ignore_index=True)
            # Keep the last occurrence per key: incoming wins over existing.
            merged = merged.drop_duplicates(subset=PRIMARY_KEY, keep="last")

        merged = merged.sort_values(["commodity", "mandi_id", "date"]).reset_index(drop=True)
        self._write(merged)

        logger.info(
            "Observation upsert: %d received, %d inserted, %d updated, %d total",
            len(incoming), inserted, updated, len(merged),
        )
        return {
            "received": int(len(incoming)),
            "inserted": int(inserted),
            "updated": int(updated),
            "total": int(len(merged)),
        }

    def _conform(self, records: pd.DataFrame) -> pd.DataFrame:
        frame = records.copy()
        for column in OBSERVATION_COLUMNS:
            if column not in frame.columns:
                frame[column] = None
        frame = frame[OBSERVATION_COLUMNS]
        frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
        for column in ("modal_price", "min_price", "max_price", "arrivals"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["quality_score"] = (
            pd.to_numeric(frame["quality_score"], errors="coerce")
            .fillna(LEGACY_QUALITY_SCORE)
            .clip(0.0, 1.0)
        )
        frame["quality_flags"] = frame["quality_flags"].fillna("").astype(str)
        # Defence in depth: the quality gate rejects non-positive prices before
        # they reach here, but a row without a usable price would poison every
        # lag and rolling feature that touched it.
        frame = frame[frame["modal_price"].notna() & (frame["modal_price"] > 0)]
        return frame.drop_duplicates(subset=PRIMARY_KEY, keep="last")

    def _write(self, frame: pd.DataFrame) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        frame.to_parquet(temp, index=False, engine="pyarrow", compression="snappy")
        temp.replace(self.path)


class QuarantineStore:
    """
    Append-only record of observations the quality gate refused.

    Kept because a rejection is a claim about the data that may itself be
    wrong. With the rows retained, a gate that is too aggressive shows up as a
    quarantine full of ordinary prices; with them deleted, it shows up as
    nothing at all until someone notices the model has quietly stopped seeing
    volatile days.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        from mandisense_ai.forecasting.config import quarantine_path

        self.path = Path(path) if path else quarantine_path()

    def read(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(self.path, engine="pyarrow")
        except Exception as exc:  # pragma: no cover - corrupt file guard
            logger.error("Quarantine unreadable at %s: %s", self.path, exc)
            return pd.DataFrame()

    def append(self, rejected: pd.DataFrame, run_id: str = "") -> int:
        if rejected is None or rejected.empty:
            return 0

        frame = rejected.copy()
        frame["quarantined_at"] = datetime.now(timezone.utc).isoformat()
        frame["run_id"] = run_id

        existing = self.read()
        merged = pd.concat([existing, frame], ignore_index=True) if not existing.empty else frame

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        merged.to_parquet(temp, index=False, engine="pyarrow", compression="snappy")
        temp.replace(self.path)

        logger.info("Quarantined %d rows to %s", len(frame), self.path)
        return int(len(frame))


def log_ingestion_run(payload: Dict[str, Any]) -> None:
    """Append one line of run telemetry — the audit trail for nightly jobs."""
    path = ingestion_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"logged_at": datetime.now(timezone.utc).isoformat(), **payload}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


@dataclass
class ForecastStore:
    """The published forecast table served by the API."""

    generated_at: str = ""
    as_of_date: str = ""
    schema_version: str = FORECAST_SCHEMA_VERSION
    config: Dict[str, Any] = field(default_factory=dict)
    model_version: str = ""
    forecasts: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------- queries

    def get(self, commodity: str, mandi_id: str) -> List[Dict[str, Any]]:
        """Full horizon curve for one series, ordered by horizon."""
        rows = [
            row
            for row in self.forecasts
            if row.get("commodity") == commodity and row.get("mandi_id") == mandi_id
        ]
        return sorted(rows, key=lambda r: r.get("horizon_days", 0))

    def get_horizon(self, commodity: str, mandi_id: str, horizon: int) -> Optional[Dict[str, Any]]:
        for row in self.get(commodity, mandi_id):
            if int(row.get("horizon_days", -1)) == int(horizon):
                return row
        return None

    def available_series(self) -> List[Dict[str, str]]:
        seen = {}
        for row in self.forecasts:
            key = (row.get("commodity"), row.get("mandi_id"))
            seen[key] = {"commodity": key[0], "mandi_id": key[1]}
        return sorted(seen.values(), key=lambda r: (r["commodity"], r["mandi_id"]))

    def age_hours(self) -> Optional[float]:
        if not self.generated_at:
            return None
        try:
            generated = datetime.fromisoformat(self.generated_at)
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - generated).total_seconds() / 3600.0
        except Exception:
            return None

    def summary(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "as_of_date": self.as_of_date,
            "model_version": self.model_version,
            "series_count": len(self.available_series()),
            "forecast_rows": len(self.forecasts),
            "age_hours": round(self.age_hours(), 2) if self.age_hours() is not None else None,
            "diagnostics": self.diagnostics,
        }

    # --------------------------------------------------------- persistence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "as_of_date": self.as_of_date,
            "model_version": self.model_version,
            "config": self.config,
            "diagnostics": self.diagnostics,
            "forecasts": self.forecasts,
        }

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path) if path else forecast_store_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        temp.replace(target)
        logger.info("Forecast store written to %s (%d rows)", target, len(self.forecasts))
        return target

    @staticmethod
    def load(path: Optional[Path] = None) -> "ForecastStore":
        target = Path(path) if path else forecast_store_path()
        payload = json.loads(target.read_text(encoding="utf-8"))

        found = str(payload.get("schema_version", "0.0.0"))
        if found.split(".")[0] != FORECAST_SCHEMA_VERSION.split(".")[0]:
            raise ValueError(
                f"Incompatible forecast store schema {found}; "
                f"this engine expects {FORECAST_SCHEMA_VERSION}"
            )

        return ForecastStore(
            generated_at=payload.get("generated_at", ""),
            as_of_date=payload.get("as_of_date", ""),
            schema_version=found,
            config=payload.get("config", {}),
            model_version=payload.get("model_version", ""),
            forecasts=payload.get("forecasts", []),
            diagnostics=payload.get("diagnostics", {}),
        )
