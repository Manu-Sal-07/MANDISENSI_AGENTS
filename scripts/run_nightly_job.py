"""
Nightly forecasting job.

Ingests the day's market prices, retrains on its own weekly cadence, rescores
every eligible series and publishes the forecast store the API reads.

Usage
-----
    python scripts/run_nightly_job.py                 # normal nightly run
    python scripts/run_nightly_job.py --seed-history  # first run: backfill archive
    python scripts/run_nightly_job.py --force-retrain # refit regardless of cadence
    python scripts/run_nightly_job.py --no-ingest     # re-forecast existing data

Scheduling
----------
Windows (Task Scheduler), nightly at 01:30:

    schtasks /create /tn "MandiSense Nightly Forecast" /sc daily /st 01:30 ^
      /tr "\"<repo>\\ms_env\\Scripts\\python.exe\" \"<repo>\\scripts\\run_nightly_job.py\"" ^
      /f

Linux (cron):

    30 1 * * *  cd /srv/mandisense && ms_env/bin/python scripts/run_nightly_job.py

Exit codes: 0 on a healthy run, 1 if the forecast stage did not publish, so a
scheduler can alert on a genuine failure rather than on log noise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.forecasting.config import DEFAULT_CONFIG  # noqa: E402
from mandisense_ai.forecasting.pipeline import run_nightly  # noqa: E402
from mandisense_ai.forecasting.store import ObservationStore  # noqa: E402


def seed_history() -> int:
    """One-time backfill of the observation store from the bundled archives.

    Seeds both the deep national benchmark history and the Karnataka
    operating region, so the forecast universe covers the markets the
    cognition layer and the TraderOS views actually serve.
    """
    from mandisense_ai.forecasting.sources.backfill import load_all_history

    history = load_all_history()
    if history.empty:
        print("No archive history found to seed.", file=sys.stderr)
        return 0

    counts = ObservationStore().upsert(history)
    print(json.dumps({"stage": "seed_history", **counts}, indent=2))
    return counts.get("total", 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-history",
        action="store_true",
        help="Backfill the observation store from the bundled archive before running",
    )
    parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Refit all horizons regardless of the weekly retrain cadence",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Skip the live fetch and re-forecast from stored observations",
    )
    parser.add_argument(
        "--as-of",
        metavar="YYYY-MM-DD",
        default=None,
        help=(
            "Score the run as of this date instead of the newest observation. "
            "Dormancy and history gaps are judged against it, so a series is "
            "only forecast if it was live on that date. Used to reproduce a "
            "run against an archive whose last trading day is in the past; "
            "the date is recorded in every forecast as as_of_date."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.seed_history:
        seed_history()

    record = run_nightly(
        config=DEFAULT_CONFIG,
        force_retrain=args.force_retrain,
        skip_ingestion=args.no_ingest,
        as_of=args.as_of,
    )

    print(json.dumps(record, indent=2, default=str))

    forecast_stage = record.get("stages", {}).get("forecast", {})
    if forecast_stage.get("status") != "OK":
        print(
            "Forecast stage did not publish; previous store left in place.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
