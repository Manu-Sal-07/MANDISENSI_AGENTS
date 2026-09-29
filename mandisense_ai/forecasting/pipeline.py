"""
Nightly pipeline orchestration.

    ingest  ->  (retrain if due)  ->  batch forecast  ->  publish

Separation of cadence is deliberate. **Ingestion runs every night** because a
day of prices that is not captured is gone — the upstream feed is a snapshot
with no history endpoint. **Retraining runs weekly**, because refitting a
model on one extra day of data changes nothing except to churn the artifact
and invite silent regressions. Batch forecasting runs every night, since it is
cheap and its inputs changed.

Failure policy: each stage degrades rather than aborting the run. If the feed
is unreachable, the job still re-forecasts from existing observations and the
published store carries the older `as_of_date` — a slightly stale forecast,
honestly labelled, beats no forecast at all. The run record says exactly what
happened either way.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pandas as pd

from mandisense_ai.forecasting.backtest import run_backtest
from mandisense_ai.forecasting.batch_predict import generate_forecasts
from mandisense_ai.forecasting.config import DEFAULT_CONFIG, ForecastConfig, model_registry_dir
from mandisense_ai.forecasting.quality import DEFAULT_QUALITY_CONFIG, score_observations
from mandisense_ai.forecasting.store import ObservationStore, QuarantineStore, log_ingestion_run
from mandisense_ai.forecasting.validation import validate_observations
from mandisense_ai.forecasting.train import ForecastBundle, train_bundle
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

RETRAIN_INTERVAL_DAYS = 7


def _stage_result(status: str, **extra: Any) -> Dict[str, Any]:
    return {"status": status, **extra}


def run_ingestion(config: ForecastConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    """
    Fetch today's prices from the live feed, grade them, and upsert them.

    Two passes, deliberately in this order and doing different jobs:

    1. `validate_observations` — the hard gate. Catches what cannot possibly
       be a price of this commodity (a unit error, a decimal slip, a stuck
       field) and refuses it outright; there is no graded version of "this is
       not a price".
    2. `score_observations` — the graded pass over whatever survives. Nothing
       here is rejected for being merely doubtful; it is priced with a
       `quality_score` that follows the row into the store and, eventually,
       into the learner as a sample weight. What the hard gate *does* reject
       is written to quarantine rather than dropped, so a gate that starts
       misbehaving is visible in that file instead of only as unexplained
       model drift months later.
    """
    from mandisense_ai.forecasting.sources.datagov import DataGovFetchError, fetch_daily_prices

    store = ObservationStore()
    try:
        fetched = fetch_daily_prices()
    except DataGovFetchError as exc:
        logger.error("Ingestion failed: %s", exc)
        return _stage_result("FEED_UNAVAILABLE", error=str(exc), rows=0)
    except Exception as exc:  # defensive: never let ingestion kill the job
        logger.error("Ingestion crashed: %s", exc, exc_info=True)
        return _stage_result("ERROR", error=str(exc), rows=0)

    if fetched.empty:
        return _stage_result("NO_RECORDS", rows=0)

    history = store.read()

    hard_accepted, hard_report = validate_observations(fetched, history=history)
    if hard_report.rejected:
        quarantined = fetched.loc[fetched.index.difference(hard_accepted.index)].copy()
        quarantined["quality_score"] = 0.0
        quarantined["quality_flags"] = "failed_hard_bounds_gate"
        QuarantineStore().append(quarantined, run_id=datetime.now(timezone.utc).isoformat())

    if hard_accepted.empty:
        return _stage_result("ALL_REJECTED", rows=0, validation=hard_report.as_dict())

    scored, graded_rejected, quality_report = score_observations(
        hard_accepted, history=history, config=DEFAULT_QUALITY_CONFIG
    )
    if not graded_rejected.empty:
        QuarantineStore().append(graded_rejected, run_id=datetime.now(timezone.utc).isoformat())

    if scored.empty:
        return _stage_result(
            "ALL_REJECTED",
            rows=0,
            validation=hard_report.as_dict(),
            quality=quality_report.as_dict(),
        )

    counts = store.upsert(scored)
    return _stage_result(
        "OK", **counts, validation=hard_report.as_dict(), quality=quality_report.as_dict()
    )


def _retrain_due(bundle_dir=None) -> bool:
    """True when no bundle exists or the current one is older than the interval."""
    directory = bundle_dir or model_registry_dir()
    metadata = directory / "metadata.json"
    if not (directory / "bundle.pkl").exists():
        return True
    if not metadata.exists():
        return True

    try:
        import json

        trained_at = json.loads(metadata.read_text(encoding="utf-8")).get("trained_at")
        if not trained_at:
            return True
        stamp = datetime.fromisoformat(trained_at)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - stamp) > timedelta(days=RETRAIN_INTERVAL_DAYS)
    except Exception:
        return True


def _score_ledger(observations: pd.DataFrame) -> Dict[str, Any]:
    """Resolve any outstanding forecast claim the new observations settle.

    Wrapped rather than called directly because monitoring must never be able
    to fail the run that produces the thing it monitors.
    """
    try:
        from mandisense_ai.forecasting.ledger import ForecastLedger

        return _stage_result("OK", **ForecastLedger().score_pending(observations))
    except Exception as exc:
        logger.warning("Ledger scoring failed: %s", exc)
        return _stage_result("ERROR", error=str(exc))


def _check_drift() -> Dict[str, Any]:
    """Compare realised performance against the backtest's own fold spread."""
    try:
        from mandisense_ai.forecasting.ledger import detect_drift

        bundle = ForecastBundle.load()
        return _stage_result("OK", **detect_drift(bundle))
    except Exception as exc:
        logger.warning("Drift check failed: %s", exc)
        return _stage_result("ERROR", error=str(exc))


def run_training(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """Refit all horizons and persist the bundle."""
    from mandisense_ai.forecasting.train import _prepare_training_frame

    # Built once and threaded through all three stages below. Each of them
    # used to call this independently — an identical ~14s feature pass over
    # the archive (absence classification, seasonal climatology, everything
    # in `build_features`) recomputed three times a night for no reason
    # other than each stage not knowing another one had just done the same
    # work moments earlier.
    try:
        prepared = _prepare_training_frame(observations, config)
    except Exception as exc:
        logger.error("Feature preparation failed: %s", exc, exc_info=True)
        return _stage_result("ERROR", error=str(exc))

    try:
        bundle = train_bundle(observations, config, prepared=prepared)
    except Exception as exc:
        logger.error("Training failed: %s", exc, exc_info=True)
        return _stage_result("ERROR", error=str(exc))

    # Interval calibration is measured on every retrain, not once at design
    # time: a band that was honest last quarter can drift as the market does.
    try:
        bundle.backtest = run_backtest(observations, config, prepared=prepared)
    except Exception as exc:
        logger.warning("Backtest skipped: %s", exc)
        bundle.backtest = {"verdict": "NOT_RUN", "error": str(exc)}

    # Row-conditional band calibration, on the same fold boundaries as above.
    # Promotion is per horizon and independent of the point model's own gate:
    # a horizon only serves the new band if it demonstrably calibrates out of
    # sample, and falls back to the pooled-residual band (already validated
    # by `bundle.backtest`) everywhere it does not.
    try:
        from mandisense_ai.forecasting.quantile import run_quantile_backtest

        bundle.quantile_backtest = run_quantile_backtest(observations, config, prepared=prepared)
        bundle.quantile_promoted_horizons = [
            int(h) for h, r in bundle.quantile_backtest.get("horizons", {}).items()
            if r.get("calibration") == "CALIBRATED"
        ]
    except Exception as exc:
        logger.warning("Quantile backtest skipped: %s", exc)
        bundle.quantile_backtest = {"verdict": "NOT_RUN", "error": str(exc)}
        bundle.quantile_promoted_horizons = []

    # Decision-policy calibration: per horizon, the threshold whose SELL/HOLD
    # precision actually cleared a real bar on held-out folds — or nothing,
    # honestly, where none did. This is what finally gives the validated
    # forecast store an actionable call; every decision engine elsewhere in
    # this codebase reads a level prediction through hand-picked thresholds
    # that were never checked against an outcome.
    try:
        from mandisense_ai.forecasting.decision import run_decision_backtest

        bundle.decision_backtest = run_decision_backtest(observations, config, prepared=prepared)
        bundle.decision_thresholds = {
            int(h): t for h, t in bundle.decision_backtest.get("chosen_thresholds", {}).items()
        }
    except Exception as exc:
        logger.warning("Decision policy backtest skipped: %s", exc)
        bundle.decision_backtest = {"verdict": "NOT_RUN", "error": str(exc)}
        bundle.decision_thresholds = {}

    bundle.save()
    return _stage_result(
        "OK",
        promoted_horizons=bundle.promoted_horizons,
        training_rows=bundle.training_rows,
        skill={str(h): v.get("skill") for h, v in bundle.validation.items()},
        skill_arrival_masked={
            str(h): v.get("skill_arrival_masked") for h, v in bundle.validation.items()
        },
        calibration=bundle.backtest.get("verdict"),
        quantile_calibration=bundle.quantile_backtest.get("verdict"),
        quantile_promoted_horizons=bundle.quantile_promoted_horizons,
        blend_promoted_horizons=sorted(bundle.blend_models.keys()),
        blend_weights=bundle.blend_weights,
        blend_vs_single_skill={
            str(h): v.get("blend_vs_single_skill") for h, v in bundle.validation.items()
        },
        decision_thresholds=bundle.decision_thresholds,
        decision_calibration=bundle.decision_backtest.get("verdict"),
        lineage_hash=bundle.lineage_hash,
        quality_summary=bundle.quality_summary,
        absence_summary=bundle.absence_summary,
    )


def run_forecast(
    observations: pd.DataFrame,
    config: ForecastConfig = DEFAULT_CONFIG,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Score every eligible series and publish the forecast store.

    `as_of` overrides the scoring date, which otherwise defaults to the newest
    observation held. Dormancy and history-gap refusals are judged against it,
    so a run reproduced against an archive is held to the same freshness rules
    as a live one rather than quietly exempted from them.
    """
    try:
        bundle = ForecastBundle.load()
    except Exception as exc:
        logger.error("No usable model bundle: %s", exc)
        return _stage_result("NO_MODEL", error=str(exc))

    if as_of is not None:
        # A run reproduced "as of" a past date must not be able to see rows
        # dated after it. Passing as_of for the freshness test alone is not
        # enough: a single later print still lands in the series history, so
        # the series is judged against a last_date in the future of the run
        # and refused as DISCONTINUOUS_HISTORY. Truncating here makes the
        # replay honest — the run sees exactly what a run on that night saw.
        cutoff = pd.Timestamp(as_of)
        before = len(observations)
        observations = observations[pd.to_datetime(observations["date"]) <= cutoff]
        logger.info(
            "as_of=%s truncated observations %d -> %d", as_of, before, len(observations)
        )
        if observations.empty:
            return _stage_result("NO_DATA", reason=f"no observations on or before {as_of}")

    try:
        store = generate_forecasts(observations, bundle, config, as_of=as_of)
    except Exception as exc:
        logger.error("Batch inference failed: %s", exc, exc_info=True)
        return _stage_result("ERROR", error=str(exc))

    # Publishing last means a failed run leaves the previous night's forecast
    # in place rather than replacing it with a broken one.
    store.save()

    # Record what was just published as a claim to be checked later. Never
    # allowed to fail the run: the forecast is already on disk and serving,
    # and losing a monitoring row is not a reason to fail a good forecast.
    ledger_result: Dict[str, Any] = {"status": "SKIPPED"}
    try:
        from mandisense_ai.forecasting.ledger import ForecastLedger

        ledger_result = ForecastLedger().record_publication(store)
        ledger_result["status"] = "OK"
    except Exception as exc:
        logger.warning("Ledger recording skipped: %s", exc)
        ledger_result = {"status": "ERROR", "error": str(exc)}

    return _stage_result("OK", ledger=ledger_result, **store.summary())


def run_nightly(
    config: ForecastConfig = DEFAULT_CONFIG,
    force_retrain: bool = False,
    skip_ingestion: bool = False,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full nightly cycle and return a structured run record.

    The record is appended to the ingestion log so a week of runs can be
    audited without re-reading application logs.
    """
    started = datetime.now(timezone.utc)
    record: Dict[str, Any] = {"started_at": started.isoformat(), "stages": {}}

    # 1. Ingest
    if skip_ingestion:
        record["stages"]["ingestion"] = _stage_result("SKIPPED")
    else:
        record["stages"]["ingestion"] = run_ingestion(config)

    observations = ObservationStore().read()
    record["observation_rows"] = int(len(observations))

    if observations.empty:
        record["stages"]["training"] = _stage_result("SKIPPED", reason="no observations")
        record["stages"]["forecast"] = _stage_result("SKIPPED", reason="no observations")
        record["status"] = "NO_DATA"
        record["duration_seconds"] = (datetime.now(timezone.utc) - started).total_seconds()
        log_ingestion_run(record)
        return record

    # 2. Score yesterday's claims against today's ground truth.
    #
    # This runs before retraining, not after, so that a retrain triggered
    # tonight is judged against a ledger that already includes everything the
    # new observations resolved. Scoring after would compare drift against a
    # ledger one day staler than the data that caused it.
    record["stages"]["ledger_scoring"] = _score_ledger(observations)

    # 3. Retrain, on its own cadence
    if force_retrain or _retrain_due():
        logger.info("Retraining is due — refitting all horizons")
        record["stages"]["training"] = run_training(observations, config)
    else:
        record["stages"]["training"] = _stage_result("NOT_DUE")

    # 4. Forecast + publish (this also appends tonight's claims to the ledger)
    record["stages"]["forecast"] = run_forecast(observations, config, as_of=as_of)
    if as_of:
        record["as_of_override"] = as_of

    # 5. Is live performance still inside the range the backtest predicted?
    #
    # Reported, not enforced. Every gate in this system was earned on
    # historical folds; this is the only check that asks whether those gates
    # still hold on data collected after promotion. It recommends demotions
    # and leaves applying them to an operator, because silently switching a
    # served model on a partial live sample is the failure mode it exists to
    # catch, not one to reproduce.
    record["stages"]["drift"] = _check_drift()

    forecast_status = record["stages"]["forecast"].get("status")
    record["status"] = "OK" if forecast_status == "OK" else "DEGRADED"
    record["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 2)

    log_ingestion_run(record)
    logger.info("Nightly run finished: %s in %.1fs", record["status"], record["duration_seconds"])
    return record
