"""An unreachable feed must fail the nightly job (exit 2), not pass as a healthy night.

Regression: GitHub's runners cannot reach data.gov.in, ingestion reported FEED_UNAVAILABLE, the job still exited 0, and the workflow committed
a store whose only change was a fresh `generated_at`, which would have made ageing data read as fresh.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def job(monkeypatch):
    spec = importlib.util.spec_from_file_location("run_nightly_job_under_test", ROOT / "scripts" / "run_nightly_job.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["run_nightly_job.py"])
    return module


def _record(ingestion, forecast="OK"):
    return {"stages": {"ingestion": {"status": ingestion}, "forecast": {"status": forecast}}}


@pytest.mark.parametrize("status", ["FEED_UNAVAILABLE", "ERROR"])
def test_unreachable_feed_fails_the_job(job, monkeypatch, status):
    monkeypatch.setattr(job, "run_nightly", lambda **kw: _record(status))
    assert job.main() == 2


@pytest.mark.parametrize("status", ["OK", "NO_RECORDS", "SKIPPED"])
def test_a_working_or_quiet_night_still_passes(job, monkeypatch, status):
    monkeypatch.setattr(job, "run_nightly", lambda **kw: _record(status))
    assert job.main() == 0


def test_forecast_failure_still_fails(job, monkeypatch):
    monkeypatch.setattr(job, "run_nightly", lambda **kw: _record("OK", forecast="ERROR"))
    assert job.main() == 1
