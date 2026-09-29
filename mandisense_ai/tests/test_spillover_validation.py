"""
Objective 2 — the spillover *validation* machinery.

`test_spillover.py` covers the estimator. This file covers the parts that
decide whether any of it is allowed to ship: panel construction, episode
randomisation, and the permutation placebo.

Those were the least-tested modules in the project and they carry the most
weight, because the engine's honesty claim rests entirely on them. A placebo
that silently degenerates — drawing zero onsets, or reusing the real dates —
would pass every estimator test while making the gate meaningless.

The placebo itself is expensive (it re-runs the whole pipeline per
permutation), so the full run is exercised once at a small permutation count
and the rest is tested at the unit level.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.spillover.config import DEFAULT_CONFIG, SHOCK_SQUEEZE
from mandisense_ai.spillover.events import ShockEpisodes
from mandisense_ai.spillover.validate import _randomise


def _index(n: int = 300) -> pd.DatetimeIndex:
    return pd.date_range("2018-01-07", periods=n, freq="W")


def _episodes(n: int, index: pd.DatetimeIndex) -> ShockEpisodes:
    return ShockEpisodes("onion", SHOCK_SQUEEZE, sorted(index[:n]))


class TestRandomisation:
    """The placebo's core move: same episode count, random dates."""

    def test_episode_count_is_preserved(self):
        index = _index()
        rng = np.random.default_rng(7)
        original = _episodes(12, index)

        randomised = _randomise(original, index, DEFAULT_CONFIG, rng)

        assert randomised.n_episodes == original.n_episodes

    def test_commodity_and_shock_type_are_preserved(self):
        index = _index()
        rng = np.random.default_rng(7)
        original = _episodes(9, index)

        randomised = _randomise(original, index, DEFAULT_CONFIG, rng)

        assert randomised.commodity == original.commodity
        assert randomised.shock_type == original.shock_type

    def test_onsets_actually_move(self):
        """If the dates did not move, the placebo would measure nothing."""
        index = _index()
        rng = np.random.default_rng(7)
        original = _episodes(15, index)

        randomised = _randomise(original, index, DEFAULT_CONFIG, rng)

        assert list(randomised.onsets) != list(original.onsets)

    def test_onsets_leave_room_for_the_forward_window(self):
        """An onset too close to the end has no forward window to measure."""
        index = _index()
        rng = np.random.default_rng(11)
        randomised = _randomise(_episodes(20, index), index, DEFAULT_CONFIG, rng)

        cutoff = index[len(index) - max(DEFAULT_CONFIG.horizons) - 1]
        assert all(onset <= cutoff for onset in randomised.onsets)

    def test_onsets_are_unique(self):
        """Sampling with replacement would understate the effective sample."""
        index = _index()
        rng = np.random.default_rng(3)
        randomised = _randomise(_episodes(40, index), index, DEFAULT_CONFIG, rng)

        assert len(set(randomised.onsets)) == len(randomised.onsets)

    def test_randomisation_is_seed_reproducible(self):
        """A placebo that cannot be reproduced cannot be audited."""
        index = _index()
        original = _episodes(10, index)

        first = _randomise(original, index, DEFAULT_CONFIG, np.random.default_rng(42))
        second = _randomise(original, index, DEFAULT_CONFIG, np.random.default_rng(42))

        assert list(first.onsets) == list(second.onsets)

    def test_different_seeds_give_different_draws(self):
        index = _index()
        original = _episodes(10, index)

        first = _randomise(original, index, DEFAULT_CONFIG, np.random.default_rng(1))
        second = _randomise(original, index, DEFAULT_CONFIG, np.random.default_rng(2))

        assert list(first.onsets) != list(second.onsets)

    def test_short_index_degrades_to_no_episodes(self):
        """Too short to hold a forward window must yield nothing, not crash."""
        index = _index(n=max(DEFAULT_CONFIG.horizons))
        rng = np.random.default_rng(5)

        randomised = _randomise(_episodes(3, index), index, DEFAULT_CONFIG, rng)

        assert randomised.n_episodes == 0

    def test_requesting_more_episodes_than_slots_is_clamped(self):
        index = _index(n=40)
        rng = np.random.default_rng(5)
        usable = len(index) - max(DEFAULT_CONFIG.horizons) - 1

        randomised = _randomise(_episodes(39, index), index, DEFAULT_CONFIG, rng)

        assert randomised.n_episodes <= usable


class TestPanel:
    """Panel construction — the input every later stage depends on."""

    def test_missing_directory_is_reported_not_crashed(self):
        from mandisense_ai.spillover.panel import build_panel

        with pytest.raises((FileNotFoundError, ValueError)):
            build_panel(Path("does_not_exist_anywhere"), DEFAULT_CONFIG)

    def test_real_panel_is_weekly_and_aligned(self):
        """The shipped panel must be what the estimator assumes it is."""
        from mandisense_ai.config.settings import settings
        from mandisense_ai.spillover.panel import build_panel

        processed = Path(settings.paths.processed_data)
        if not processed.exists():
            pytest.skip("processed datasets not present in this checkout")

        panel = build_panel(processed, DEFAULT_CONFIG)

        assert not panel.returns.empty
        # Returns, regimes and prices must share one index, or a shock date
        # would address a different week in each frame.
        assert panel.returns.index.equals(panel.regimes.index)
        assert list(panel.returns.columns) == list(panel.regimes.columns)

    def test_panel_has_no_duplicate_dates(self):
        from mandisense_ai.config.settings import settings
        from mandisense_ai.spillover.panel import build_panel

        processed = Path(settings.paths.processed_data)
        if not processed.exists():
            pytest.skip("processed datasets not present in this checkout")

        panel = build_panel(processed, DEFAULT_CONFIG)
        assert panel.returns.index.is_unique
        assert panel.returns.index.is_monotonic_increasing


@pytest.mark.slow
class TestPlaceboEndToEnd:
    """One real placebo run, at a small permutation count."""

    def test_placebo_reports_a_comparable_distribution(self):
        from mandisense_ai.config.settings import settings
        from mandisense_ai.spillover.validate import run_placebo

        processed = Path(settings.paths.processed_data)
        if not processed.exists():
            pytest.skip("processed datasets not present in this checkout")

        result = run_placebo(processed, DEFAULT_CONFIG, n_permutations=5)

        # The full diagnostic contract, because the verdict alone is not
        # auditable - a reviewer needs the distribution it was derived from.
        for key in (
            "observed_significant_edges",
            "n_permutations",
            "placebo_mean",
            "placebo_std",
            "placebo_p95",
            "empirical_p_value",
            "verdict",
        ):
            assert key in result, f"placebo result is missing '{key}'"

        assert result["n_permutations"] == 5
        assert result["observed_significant_edges"] >= 0
        assert 0.0 <= result["empirical_p_value"] <= 1.0
        assert result["verdict"] in ("PASS", "FAIL")

        # The verdict must follow from the p-value rather than being set
        # independently, or the gate could pass while the evidence says fail.
        if result["empirical_p_value"] <= 0.05:
            assert result["verdict"] == "PASS"
        else:
            assert result["verdict"] == "FAIL"

    def test_placebo_is_reproducible_at_a_fixed_seed(self):
        """A gate whose verdict moves between identical runs is not a gate."""
        from mandisense_ai.config.settings import settings
        from mandisense_ai.spillover.validate import run_placebo

        processed = Path(settings.paths.processed_data)
        if not processed.exists():
            pytest.skip("processed datasets not present in this checkout")

        first = run_placebo(processed, DEFAULT_CONFIG, n_permutations=3)
        second = run_placebo(processed, DEFAULT_CONFIG, n_permutations=3)

        assert first["observed_significant_edges"] == second["observed_significant_edges"]
        assert first["placebo_mean"] == second["placebo_mean"]
        assert first["verdict"] == second["verdict"]
