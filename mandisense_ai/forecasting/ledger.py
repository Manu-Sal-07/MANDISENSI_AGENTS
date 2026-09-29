"""
Closed-loop outcome ledger: did the published forecast turn out to be right?

Every gate built into this system so far — the point model's baseline gate,
the interval's coverage calibration, the blend's promotion check, the
decision policy's precision threshold — was validated against *history*, at
training time. None of them ever looks at what happened after publication.
That gap is what this module closes.

What it replaces
----------------
`OperationalVerificationEngine` claims to be exactly this ("Closed-Loop
Operational Verification / Learning from real-world consequences") and is
not. It compares one prediction against another prediction, never against a
realised price; it starts every plan at a hardcoded 0.5 effectiveness and
adjusts by fixed increments; and with no outcomes recorded at all it reports
`overall_effectiveness: 1.0`, which `/v1/institutional/metrics` publishes as
a headline number. A verification layer whose default answer is "perfect"
is worse than none, because it looks like evidence.

How this one works
------------------
1. Every published forecast row is appended here when the nightly job
   publishes it — the prediction, its interval, the decision, the threshold
   it was judged against, and the date it is a claim about.
2. When ingestion later brings in the actual price for that target date, the
   row is scored: was the direction right, did the price land inside the 90%
   and 50% bands, and was the SELL/HOLD call correct.
3. `detect_drift` compares live performance against what the backtest itself
   predicted — specifically the spread across its own walk-forward folds,
   not a hand-picked tolerance. A model performing outside the range its own
   validation produced is the signal that its promotion no longer holds.

The honest constraint
---------------------
This ledger starts empty and fills at the speed of the calendar: horizons of
1-7 days mean days to weeks before live numbers mean anything, and it only
fills at all if the nightly job actually runs. Every reader below reports
`INSUFFICIENT_EVIDENCE` until it has enough scored rows, rather than
computing a confident-looking rate from four observations. Until then the
backtest remains the calibration source of record, and the metrics endpoint
should say so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.config import ledger_path
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

LEDGER_COLUMNS = [
    "recorded_at",
    "as_of_date",
    "commodity",
    "mandi_id",
    "horizon_days",
    "target_date",
    "base_price",
    "forecast_price",
    "expected_change_pct",
    "direction",
    "p05",
    "p25",
    "p75",
    "p95",
    "interval_source",
    "prediction_source",
    "decision",
    "probability_of_decline",
    "model_skill",
    # Filled in later, once the target date's actual price is observed.
    "actual_price",
    "actual_change_pct",
    "direction_correct",
    "inside_90",
    "inside_50",
    "decision_correct",
    "scored_at",
]

# A forecast is a claim about a specific date. Re-publishing the same claim
# (the nightly job runs again before any new data arrives) must not create a
# second row, or the same prediction would be counted twice in every rate.
PRIMARY_KEY = ["as_of_date", "commodity", "mandi_id", "horizon_days"]

# Below this many scored rows, no rate is reported. Four correct calls out of
# five is not evidence of an 80% hit rate, and publishing it as one is how a
# monitoring system starts lying earlier than the thing it monitors.
MIN_SCORED_FOR_RATE = 30

# How far from the target date a price may sit and still count as the
# outcome. Mandis do not trade every day; the same slack the training
# targets use.
OUTCOME_TOLERANCE_DAYS = 3


class ForecastLedger:
    """Append-only store of published forecasts and their realised outcomes."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else ledger_path()

    # ----------------------------------------------------------- reading

    def read(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=LEDGER_COLUMNS)
        try:
            frame = pd.read_parquet(self.path, engine="pyarrow")
        except Exception as exc:  # pragma: no cover - corrupt file guard
            logger.error("Ledger unreadable at %s: %s", self.path, exc)
            return pd.DataFrame(columns=LEDGER_COLUMNS)
        for column in LEDGER_COLUMNS:
            if column not in frame.columns:
                frame[column] = None
        return frame

    def _write(self, frame: pd.DataFrame) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        frame.to_parquet(temp, index=False, engine="pyarrow", compression="snappy")
        temp.replace(self.path)

    # ----------------------------------------------------------- writing

    def record_publication(self, store: Any) -> Dict[str, int]:
        """
        Append every serveable row of a freshly published forecast store.

        Idempotent on `(as_of_date, commodity, mandi_id, horizon_days)`:
        re-running the nightly job before new data arrives republishes the
        same claims, and those must not be counted twice.
        """
        rows: List[Dict[str, Any]] = []
        recorded_at = datetime.now(timezone.utc).isoformat()

        for row in getattr(store, "forecasts", []) or []:
            if row.get("status") != "OK" or not row.get("target_date"):
                continue
            interval = row.get("interval") or {}
            rows.append({
                "recorded_at": recorded_at,
                "as_of_date": row.get("as_of_date"),
                "commodity": row.get("commodity"),
                "mandi_id": row.get("mandi_id"),
                "horizon_days": row.get("horizon_days"),
                "target_date": row.get("target_date"),
                "base_price": row.get("last_observed_price"),
                "forecast_price": row.get("forecast_price"),
                "expected_change_pct": row.get("expected_change_pct"),
                "direction": row.get("direction"),
                "p05": interval.get("p05"),
                "p25": interval.get("p25"),
                "p75": interval.get("p75"),
                "p95": interval.get("p95"),
                "interval_source": row.get("interval_source"),
                "prediction_source": row.get("prediction_source"),
                "decision": row.get("decision"),
                "probability_of_decline": row.get("decision_probability_of_decline"),
                "model_skill": row.get("model_skill"),
                "actual_price": None,
                "actual_change_pct": None,
                "direction_correct": None,
                "inside_90": None,
                "inside_50": None,
                "decision_correct": None,
                "scored_at": None,
            })

        if not rows:
            return {"received": 0, "inserted": 0, "duplicate": 0}

        incoming = pd.DataFrame(rows)[LEDGER_COLUMNS]
        existing = self.read()

        if existing.empty:
            merged, inserted, duplicate = incoming, len(incoming), 0
        else:
            existing_keys = set(
                map(tuple, existing[PRIMARY_KEY].astype(str).to_numpy().tolist())
            )
            incoming_keys = list(
                map(tuple, incoming[PRIMARY_KEY].astype(str).to_numpy().tolist())
            )
            keep_mask = [key not in existing_keys for key in incoming_keys]
            fresh = incoming[keep_mask]
            inserted, duplicate = len(fresh), len(incoming) - len(fresh)
            merged = pd.concat([existing, fresh], ignore_index=True) if inserted else existing

        self._write(merged)
        logger.info(
            "Ledger: %d rows received, %d recorded, %d already present",
            len(incoming), inserted, duplicate,
        )
        return {"received": int(len(incoming)), "inserted": int(inserted), "duplicate": int(duplicate)}

    def score_pending(self, observations: pd.DataFrame) -> Dict[str, int]:
        """
        Fill in outcomes for any claim whose target date has now been observed.

        A row is scored once and never rescored — the realised price of a past
        date does not change, and rescoring would let a later run quietly
        revise history.
        """
        ledger = self.read()
        if ledger.empty:
            return {"pending": 0, "scored": 0}

        pending_mask = ledger["actual_price"].isna()
        if not pending_mask.any():
            return {"pending": 0, "scored": 0}

        actuals = observations[["date", "commodity", "mandi_id", "modal_price"]].copy()
        actuals["date"] = pd.to_datetime(actuals["date"])
        actuals = actuals.dropna(subset=["date", "modal_price"])

        scored_at = datetime.now(timezone.utc).isoformat()
        scored = 0

        for index in ledger.index[pending_mask]:
            row = ledger.loc[index]
            try:
                target = pd.Timestamp(row["target_date"])
            except Exception:
                continue

            series = actuals[
                (actuals["commodity"] == row["commodity"])
                & (actuals["mandi_id"] == row["mandi_id"])
            ]
            if series.empty:
                continue

            # Nearest observation at or after the target date, within slack.
            window = series[
                (series["date"] >= target)
                & (series["date"] <= target + pd.Timedelta(days=OUTCOME_TOLERANCE_DAYS))
            ].sort_values("date")
            if window.empty:
                continue

            actual_price = float(window.iloc[0]["modal_price"])
            base_price = row["base_price"]
            if not base_price or float(base_price) <= 0:
                continue
            base_price = float(base_price)

            actual_change_pct = (actual_price - base_price) / base_price * 100.0
            declined = actual_change_pct < 0

            ledger.at[index, "actual_price"] = actual_price
            ledger.at[index, "actual_change_pct"] = actual_change_pct
            ledger.at[index, "scored_at"] = scored_at

            expected = row["expected_change_pct"]
            if expected is not None and not pd.isna(expected):
                ledger.at[index, "direction_correct"] = bool(
                    (float(expected) < 0) == declined
                )

            if row["p05"] is not None and not pd.isna(row["p05"]):
                ledger.at[index, "inside_90"] = bool(
                    float(row["p05"]) <= actual_price <= float(row["p95"])
                )
            if row["p25"] is not None and not pd.isna(row["p25"]):
                ledger.at[index, "inside_50"] = bool(
                    float(row["p25"]) <= actual_price <= float(row["p75"])
                )

            # WAIT is not a directional claim, so it is left unscored rather
            # than counted as a free win or a loss.
            decision = row["decision"]
            if decision == "SELL":
                ledger.at[index, "decision_correct"] = bool(declined)
            elif decision == "HOLD":
                ledger.at[index, "decision_correct"] = bool(not declined)

            scored += 1

        if scored:
            self._write(ledger)
        logger.info("Ledger: scored %d newly-resolved forecasts", scored)
        return {"pending": int(pending_mask.sum()), "scored": int(scored)}

    # ---------------------------------------------------------- reporting

    def live_performance(self, horizon: Optional[int] = None) -> Dict[str, Any]:
        """
        Realised performance, or an honest statement that there is not enough
        of it yet.
        """
        ledger = self.read()
        if ledger.empty:
            return {"status": "NO_RECORDS", "scored": 0}

        scored = ledger[ledger["actual_price"].notna()]
        if horizon is not None:
            scored = scored[scored["horizon_days"] == horizon]

        n = int(len(scored))
        if n < MIN_SCORED_FOR_RATE:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "scored": n,
                "required": MIN_SCORED_FOR_RATE,
                "note": (
                    f"{n} scored outcome(s); rates are withheld below "
                    f"{MIN_SCORED_FOR_RATE} because a handful of results is "
                    "not a hit rate."
                ),
            }

        def _rate(column: str) -> Optional[float]:
            values = scored[column].dropna()
            return round(float(values.mean()), 4) if len(values) else None

        decided = scored[scored["decision"].isin(["SELL", "HOLD"])]
        return {
            "status": "OK",
            "scored": n,
            "horizon_days": horizon,
            "directional_accuracy": _rate("direction_correct"),
            "coverage_90": _rate("inside_90"),
            "coverage_50": _rate("inside_50"),
            "decision_precision": _rate("decision_correct"),
            "decision_calls": int(len(decided)),
            "decision_coverage": round(len(decided) / n, 4) if n else 0.0,
        }


def _fold_spread(fold_reports: List[Dict[str, Any]], key: str) -> Optional[tuple]:
    """(min, max) of a metric across the backtest's own folds."""
    values = [f[key] for f in fold_reports or [] if f.get(key) is not None]
    if len(values) < 2:
        return None
    return (float(min(values)), float(max(values)))


def detect_drift(bundle: Any, ledger: Optional[ForecastLedger] = None) -> Dict[str, Any]:
    """
    Has live performance fallen outside what the backtest itself predicted?

    The comparison band is the spread the model's *own* walk-forward folds
    produced, not a tolerance invented here. If a horizon's folds ranged
    between 0.75 and 0.98 coverage, live coverage inside that range is
    normal variation; below it is the model doing something its validation
    never saw, which is precisely the condition its promotion was granted
    under and no longer holds.

    Returns a per-horizon verdict and, where drift is found, the specific
    demotion to apply. It recommends rather than mutates, so the caller
    decides when a demotion takes effect.
    """
    ledger = ledger or ForecastLedger()
    horizons: Dict[str, Any] = {}
    demotions: List[Dict[str, Any]] = []

    for horizon in sorted(getattr(bundle, "promoted_horizons", []) or []):
        live = ledger.live_performance(horizon)
        if live.get("status") != "OK":
            horizons[str(horizon)] = {"verdict": "INSUFFICIENT_EVIDENCE", "live": live}
            continue

        report: Dict[str, Any] = {"verdict": "WITHIN_EXPECTED_RANGE", "live": live, "checks": {}}

        backtest_horizons = (getattr(bundle, "backtest", {}) or {}).get("horizons", {})
        fold_reports = (backtest_horizons.get(str(horizon)) or {}).get("fold_reports", [])
        coverage_band = _fold_spread(fold_reports, "coverage_90")
        live_coverage = live.get("coverage_90")

        if coverage_band and live_coverage is not None:
            low, high = coverage_band
            within = low <= live_coverage <= high
            report["checks"]["coverage_90"] = {
                "live": live_coverage,
                "backtest_fold_range": [round(low, 4), round(high, 4)],
                "within": within,
            }
            if live_coverage < low:
                report["verdict"] = "DRIFTED"
                demotions.append({
                    "horizon": horizon,
                    "action": "DEMOTE_INTERVAL_TO_POOLED",
                    "reason": (
                        f"live 90% coverage {live_coverage:.3f} is below the "
                        f"{low:.3f}-{high:.3f} range this model's own folds produced"
                    ),
                })

        # The decision threshold was promoted on a measured precision floor;
        # the same floor is what it has to keep clearing live.
        live_precision = live.get("decision_precision")
        # Horizon keys survive a JSON round-trip as strings and a pickle
        # round-trip as ints, so look under both rather than depending on
        # which way this bundle happened to be persisted.
        thresholds = getattr(bundle, "decision_thresholds", {}) or {}
        threshold = thresholds.get(horizon, thresholds.get(str(horizon)))
        if threshold is not None and live_precision is not None:
            from mandisense_ai.forecasting.decision import MIN_ACCEPTABLE_PRECISION

            clears = live_precision >= MIN_ACCEPTABLE_PRECISION
            report["checks"]["decision_precision"] = {
                "live": live_precision,
                "required": MIN_ACCEPTABLE_PRECISION,
                "clears": clears,
            }
            if not clears:
                report["verdict"] = "DRIFTED"
                demotions.append({
                    "horizon": horizon,
                    "action": "DEMOTE_DECISION_TO_WAIT",
                    "reason": (
                        f"live decision precision {live_precision:.3f} is below the "
                        f"{MIN_ACCEPTABLE_PRECISION} floor its promotion required"
                    ),
                })

        horizons[str(horizon)] = report

    drifted = [h for h, r in horizons.items() if r.get("verdict") == "DRIFTED"]
    return {
        "horizons": horizons,
        "drifted_horizons": drifted,
        "demotions": demotions,
        "verdict": "DRIFT_DETECTED" if drifted else (
            "OK" if any(r.get("verdict") == "WITHIN_EXPECTED_RANGE" for r in horizons.values())
            else "INSUFFICIENT_EVIDENCE"
        ),
    }
