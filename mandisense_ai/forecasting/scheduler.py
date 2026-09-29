"""
In-process nightly scheduler.

`pipeline.py`'s own docstring assumed external infrastructure — cron, Windows
Task Scheduler — would call `run_nightly` on a schedule. Measured against the
actual run log, that never happened: eleven runs total, every one of them
triggered manually within a single two-hour window on one day, and the
published forecast store's `as_of_date` sat more than four months stale by
the time this was audited. A well-designed pipeline that nothing ever calls
produces the same forecasts as no pipeline at all.

This runs the job from inside the same process that serves the API, so
"the forecasting system is scheduled" stops depending on someone provisioning
separate infrastructure that this deployment does not have. It does not
replace `scripts/run_nightly_job.py` for a real production rollout with its
own ops tooling — the cron/Task Scheduler invocations documented there remain
the right answer once such tooling exists — but it means forecasts keep
moving in every environment this API actually runs in, including this one.

The check is deliberately state-free: due-ness is read from the forecast
store's own `age_hours` rather than kept as separate scheduler bookkeeping
that could drift from what the store actually reflects.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# A full nightly run (ingest + weekly-cadence retrain + score + publish) was
# measured at well under a minute against the full archive; checking every
# half hour costs nothing and keeps the lag between "due" and "run" small.
POLL_INTERVAL_SECONDS = 60 * 30

# The forecast store's own staleness policy (`fresh_max_age_hours`, currently
# 30) governs what callers are *told*. This governs when the scheduler itself
# tries again — set a little tighter so a fresh run is usually already
# published before anything downstream would report degraded.
DUE_AFTER_HOURS = 20.0


def _is_due() -> bool:
    from mandisense_ai.forecasting.service import get_forecast_service

    service = get_forecast_service()
    service.reload()
    status = service.status()
    if not status.get("available"):
        return True
    age = status.get("age_hours")
    return age is None or age > DUE_AFTER_HOURS


def run_nightly_job_sync() -> Dict[str, Any]:
    """Blocking entry point. Run on a worker thread — never on the event loop
    directly, since a multi-horizon XGBoost refit is real CPU work."""
    from mandisense_ai.forecasting.pipeline import run_nightly

    return run_nightly()


async def forecast_scheduler_loop(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    """
    Runs for the lifetime of the process.

    Never lets a failed run take the loop down: a scheduler that dies from one
    bad night stays dead until someone notices the silence and restarts the
    whole API, which is a worse failure mode than logging the exception and
    trying again at the next poll.
    """
    logger.info(
        "[ForecastScheduler] Starting (poll every %.0fs, due after %.0fh)",
        poll_interval, DUE_AFTER_HOURS,
    )
    while True:
        try:
            if _is_due():
                logger.info(
                    "[ForecastScheduler] Forecast store is due for refresh — "
                    "running the nightly pipeline"
                )
                record = await asyncio.to_thread(run_nightly_job_sync)
                logger.info(
                    "[ForecastScheduler] Nightly run finished: status=%s duration=%.1fs",
                    record.get("status"), record.get("duration_seconds", 0.0),
                )
            else:
                logger.debug("[ForecastScheduler] Forecast store is fresh — skipping")
        except Exception as exc:  # defensive: the loop must survive any single bad run
            logger.error("[ForecastScheduler] Nightly run crashed: %s", exc, exc_info=True)

        await asyncio.sleep(poll_interval)
