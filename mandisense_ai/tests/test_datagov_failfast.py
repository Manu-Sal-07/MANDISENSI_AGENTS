"""An unreachable data.gov.in must be reported quickly, not after every slice has timed out (30 slices x 3 tries x 30 s ~ 48 minutes)."""
import pytest

from mandisense_ai.forecasting.sources import datagov


def test_aborts_after_the_first_few_slices_when_nothing_has_ever_worked(monkeypatch):
    monkeypatch.setenv("DATAGOV_API_KEY", "test-key")
    calls = []

    def dead(url):
        calls.append(url)
        raise datagov.DataGovFetchError("unreachable")

    monkeypatch.setattr(datagov, "_request", dead)
    with pytest.raises(datagov.DataGovFetchError, match="aborting early"):
        datagov.fetch_daily_prices(states=["A", "B", "C"], commodities=["tomato", "onion", "potato", "garlic", "ginger"])
    assert len(calls) == datagov.FAIL_FAST_AFTER  # 3 slices tried, not 15


def test_one_success_keeps_partial_failure_tolerance(monkeypatch):
    monkeypatch.setenv("DATAGOV_API_KEY", "test-key")
    state = {"n": 0}

    def flaky(url):
        state["n"] += 1
        if state["n"] == 1:
            return {"records": [], "total": 0}  # the first slice works (no rows is fine)
        raise datagov.DataGovFetchError("down")

    monkeypatch.setattr(datagov, "_request", flaky)
    frame = datagov.fetch_daily_prices(states=["A"], commodities=["tomato", "onion", "potato", "garlic", "ginger"])
    assert len(frame) == 0 and state["n"] == 5  # every slice was still attempted
