"""
Refresh the data from a machine that can reach data.gov.in, verify it, and publish it (commit, and optionally push so Render redeploys).

    python scripts/refresh_and_publish.py                 # ingest, re-score, test, commit locally
    python scripts/refresh_and_publish.py --push          # ... and push to origin/main (Render then redeploys, about 3 minutes)
    python scripts/refresh_and_publish.py --dry-run       # ingest and test only; leave the working tree as is, commit nothing

GitHub's runners cannot reach api.data.gov.in (measured), so this is the real refresh path. It refuses to publish when ingestion failed
(`run_nightly_job.py` exits 2) or when no new observations arrived, so a fresh-looking timestamp can never stand in for fresh data.
Set DATAGOV_API_KEY (free, https://data.gov.in) to avoid the shared sample key's rate limit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTEFACTS = [
    "data/observations/market_observations.parquet",
    "mandisense_ai/models/forecasts/forecast_store.json",
    "mandisense_ai/models/forecast_models/bundle.pkl",
    "mandisense_ai/models/forecast_models/metadata.json",
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--push", action="store_true", help="push the commit to origin main")
    ap.add_argument("--dry-run", action="store_true", help="ingest and test, but do not commit")
    a = ap.parse_args()

    before = subprocess.run(["git", "status", "--porcelain", "--", *ARTEFACTS], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if before and not a.dry_run:
        print("The data artefacts already have uncommitted changes; commit or discard them first:\n" + before)
        return 1

    job = run([sys.executable, "scripts/run_nightly_job.py"], check=False)
    if job.returncode == 2:
        print("\nIngestion failed (the feed is unreachable from this machine). Nothing was published.")
        run(["git", "checkout", "--", *ARTEFACTS], check=False)
        return 2
    if job.returncode != 0:
        print(f"\nThe nightly job failed (exit {job.returncode}). Nothing was published.")
        return job.returncode

    run([sys.executable, "-m", "pytest", "mandisense_ai/tests/test_forecasting.py", "mandisense_ai/tests/test_market_insights.py",
         "-q", "-p", "no:cacheprovider"])

    unchanged = subprocess.run(["git", "diff", "--quiet", "--", ARTEFACTS[0]], cwd=ROOT).returncode == 0
    if unchanged:
        print("\nNo new observations arrived; nothing to publish.")
        run(["git", "checkout", "--", *ARTEFACTS], check=False)
        return 0
    if a.dry_run:
        print("\nDry run: new observations arrived and the checks passed; leaving the working tree changed, committing nothing.")
        return 0

    run(["git", "add", "-f", *ARTEFACTS])
    run(["git", "commit", "-m", f"Data refresh {dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"])
    if a.push:
        run(["git", "pull", "--rebase", "origin", "main"])
        run(["git", "push", "origin", "HEAD:main"])
        print("\nPushed. Render redeploys in about three minutes; then check /v1/health for forecast freshness.")
    else:
        print("\nCommitted locally. Re-run with --push (or `git push origin HEAD:main`) to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
