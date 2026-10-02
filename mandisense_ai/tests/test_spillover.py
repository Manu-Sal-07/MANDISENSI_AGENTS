"""
Tests for the cross-commodity spillover engine.

Coverage is organised around the properties that have to hold for the feature
to be trustworthy rather than merely functional:

  * the estimator never looks ahead
  * the common factor is genuinely removed
  * episodes are counted once, not once per week
  * multiple testing is corrected over the full family
  * an unbuilt or corrupt artifact degrades quietly and never breaks a request
  * a synthetic ground truth is actually recovered
"""

import json

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.spillover.common_factor import decompose
from mandisense_ai.spillover.config import (
    SHOCK_GLUT,
    SHOCK_SQUEEZE,
    SpilloverConfig,
)
from mandisense_ai.spillover.estimator import (
    STATUS_INSUFFICIENT,
    STATUS_SIGNIFICANT,
    HorizonEffect,
    _forward_cumulative_returns,
    benjamini_hochberg,
    estimate_pair,
    peak_effect,
)
from mandisense_ai.spillover.events import ShockEpisodes, _cluster_onsets, detect_episodes
from mandisense_ai.spillover.matrix import (
    SCHEMA_VERSION,
    SpilloverEdge,
    SpilloverMatrix,
)
from mandisense_ai.spillover.service import SpilloverService


# --------------------------------------------------------------------- helpers


def _weekly_index(n, start="2020-01-05"):
    return pd.date_range(start, periods=n, freq="W")


def _make_config(**overrides):
    base = dict(
        min_episodes=3,
        bootstrap_iterations=300,
        horizons=(1, 2, 3),
        min_gap_periods=4,
        random_seed=7,
    )
    base.update(overrides)
    return SpilloverConfig(**base)


# ------------------------------------------------------------ forward windows


class TestForwardWindows:
    def test_window_is_strictly_forward(self):
        series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5], index=_weekly_index(5))
        forward = _forward_cumulative_returns(series, 2)
        # At t0 the window covers t1+t2 only; t0 itself must be excluded.
        assert forward.iloc[0] == pytest.approx(0.5)
        assert forward.iloc[1] == pytest.approx(0.7)

    def test_truncated_windows_are_nan_not_padded(self):
        series = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5], index=_weekly_index(5))
        forward = _forward_cumulative_returns(series, 3)
        assert pd.isna(forward.iloc[-1])
        assert pd.isna(forward.iloc[-2])

    def test_horizon_one_is_the_next_period(self):
        series = pd.Series([1.0, 2.0, 3.0], index=_weekly_index(3))
        forward = _forward_cumulative_returns(series, 1)
        assert forward.iloc[0] == pytest.approx(2.0)
        assert forward.iloc[1] == pytest.approx(3.0)
        assert pd.isna(forward.iloc[2])


# -------------------------------------------------------------- common factor


class TestCommonFactor:
    def test_leave_one_out_is_used_when_the_panel_allows_it(self):
        rng = np.random.default_rng(0)
        index = _weekly_index(200)
        common = rng.normal(size=200)
        frame = pd.DataFrame(
            {name: common * beta + rng.normal(scale=0.5, size=200)
             for name, beta in [("a", 1.0), ("b", 0.8), ("c", -0.5)]},
            index=index,
        )
        result = decompose(frame, _make_config(remove_seasonality=False))
        assert result.leave_one_out is True
        assert result.as_dict()["mechanical_residual_correlation"] == 0.0

    def test_two_commodity_panel_falls_back_to_the_panel_factor(self):
        """Leave-one-out is undefined with two series; the fallback must hold."""
        rng = np.random.default_rng(5)
        index = _weekly_index(200)
        common = rng.normal(size=200)
        frame = pd.DataFrame(
            {"a": common + rng.normal(scale=0.3, size=200),
             "b": common + rng.normal(scale=0.3, size=200)},
            index=index,
        )
        result = decompose(frame, _make_config(remove_seasonality=False))
        assert result.leave_one_out is False
        for column in frame.columns:
            assert abs(result.residuals[column].corr(result.factor)) < 1e-9

    def test_shared_shock_stops_looking_like_positive_co_movement(self):
        """
        Commodities driven by one common shock and nothing else must lose their
        strong positive co-movement. This is the property that stops "it rained
        everywhere" being sold as transmission.

        The assertion is on *signed* correlation. Projecting a common component
        out of k series mechanically leaves residuals negatively correlated by
        roughly -1/(k-1); that is a known property of the method, documented in
        common_factor, and not something this test should pretend away.
        """
        rng = np.random.default_rng(1)
        index = _weekly_index(300)
        frame = pd.DataFrame(
            {name: rng.normal(size=300) * 0 + rng.normal(scale=0.1, size=300)
             for name in ("a", "b", "c")},
            index=index,
        )
        common = rng.normal(size=300)
        for name in frame.columns:
            frame[name] = frame[name] + common

        upper = np.triu_indices(3, k=1)
        raw_corr = frame.corr().values[upper].mean()
        result = decompose(frame, _make_config(remove_seasonality=False))
        residual_corr = result.residuals.corr().values[upper].mean()

        assert raw_corr > 0.9, "inputs should start strongly co-moving"
        assert residual_corr <= 0.0, "positive co-movement must be removed"

    def test_zero_variance_column_is_rejected_loudly(self):
        index = _weekly_index(150)
        frame = pd.DataFrame(
            {"a": np.random.default_rng(2).normal(size=150), "flat": np.zeros(150)},
            index=index,
        )
        with pytest.raises(ValueError, match="Zero-variance"):
            decompose(frame, _make_config(remove_seasonality=False))

    def test_empty_panel_is_rejected(self):
        with pytest.raises(ValueError):
            decompose(pd.DataFrame(), _make_config())


# ----------------------------------------------------------- episode counting


class TestEpisodeClustering:
    def test_sustained_regime_counts_once(self):
        index = _weekly_index(20)
        flags = pd.Series([False] * 5 + [True] * 10 + [False] * 5, index=index)
        assert len(_cluster_onsets(flags, 4)) == 1

    def test_separated_episodes_count_separately(self):
        index = _weekly_index(30)
        values = [False] * 5 + [True] * 2 + [False] * 10 + [True] * 2 + [False] * 11
        assert len(_cluster_onsets(pd.Series(values, index=index), 4)) == 2

    def test_flicker_within_gap_is_one_episode(self):
        index = _weekly_index(20)
        values = [False, True, False, True, False] + [False] * 15
        assert len(_cluster_onsets(pd.Series(values, index=index), 4)) == 1

    def test_no_regime_yields_no_episodes(self):
        index = _weekly_index(10)
        assert _cluster_onsets(pd.Series([False] * 10, index=index), 4) == []

    def test_detect_episodes_covers_both_directions(self):
        index = _weekly_index(30)
        regimes = pd.DataFrame(
            {"onion": ["normal"] * 5 + ["squeeze"] * 5 + ["normal"] * 10 + ["glut"] * 10},
            index=index,
        )
        found = detect_episodes(regimes, _make_config())
        assert found[f"onion:{SHOCK_SQUEEZE}"].n_episodes == 1
        assert found[f"onion:{SHOCK_GLUT}"].n_episodes == 1

    def test_missing_regime_data_is_not_fatal(self):
        assert detect_episodes(pd.DataFrame(), _make_config()) == {}


# ------------------------------------------------------ multiple-test control


class TestBenjaminiHochberg:
    def test_pure_noise_yields_no_discoveries(self):
        rng = np.random.default_rng(3)
        p_values = list(rng.uniform(size=200))
        assert sum(benjamini_hochberg(p_values, 0.10)) == 0

    def test_strong_signal_is_recovered(self):
        rng = np.random.default_rng(4)
        p_values = [1e-8] * 10 + list(rng.uniform(size=90))
        assert sum(benjamini_hochberg(p_values, 0.10)) >= 10

    def test_result_is_positionally_aligned(self):
        assert benjamini_hochberg([0.9, 1e-9, 0.8], 0.10) == [False, True, False]

    def test_nan_is_a_non_discovery(self):
        assert benjamini_hochberg([float("nan"), 1e-9], 0.10) == [False, True]

    def test_empty_input(self):
        assert benjamini_hochberg([], 0.10) == []


# ------------------------------------------------------------- the estimator


class TestEstimator:
    def _panel_with_planted_effect(self, lag=2, effect=0.20, n=320):
        """Source shocks at known times; target moves `effect` exactly `lag` later."""
        rng = np.random.default_rng(11)
        index = _weekly_index(n)
        source = pd.Series(rng.normal(scale=0.02, size=n), index=index)
        target = pd.Series(rng.normal(scale=0.02, size=n), index=index)

        onsets = [index[i] for i in range(20, n - 20, 25)]
        for onset in onsets:
            position = index.get_loc(onset)
            target.iloc[position + lag] += effect

        residuals = pd.DataFrame({"src": source, "tgt": target})
        episodes = ShockEpisodes("src", SHOCK_SQUEEZE, onsets)
        return residuals, episodes

    def test_planted_effect_is_recovered_at_the_right_horizon(self):
        residuals, episodes = self._panel_with_planted_effect(lag=2, effect=0.20)
        config = _make_config(horizons=(1, 2, 3, 4))
        effects = estimate_pair(residuals, "src", "tgt", episodes, config)
        peak = peak_effect(effects)

        by_horizon = {e.horizon: e for e in effects}
        # The effect lands in period lag+1 counting from the onset, so every
        # window from h=2 onward contains it, and h=1 does not.
        assert by_horizon[1].elasticity < 0.05
        assert by_horizon[2].elasticity == pytest.approx(0.20, abs=0.05)
        assert peak.is_significant

    def test_no_effect_is_not_invented(self):
        rng = np.random.default_rng(12)
        index = _weekly_index(300)
        residuals = pd.DataFrame(
            {"src": rng.normal(scale=0.02, size=300),
             "tgt": rng.normal(scale=0.02, size=300)},
            index=index,
        )
        onsets = [index[i] for i in range(20, 280, 25)]
        episodes = ShockEpisodes("src", SHOCK_SQUEEZE, onsets)
        effects = estimate_pair(residuals, "src", "tgt", episodes, _make_config())
        assert not any(e.is_significant for e in effects)

    def test_below_episode_floor_is_marked_insufficient(self):
        residuals, episodes = self._panel_with_planted_effect()
        truncated = ShockEpisodes("src", SHOCK_SQUEEZE, episodes.onsets[:2])
        config = _make_config(min_episodes=8)
        effects = estimate_pair(residuals, "src", "tgt", truncated, config)
        assert all(e.status == STATUS_INSUFFICIENT for e in effects)

    def test_estimation_is_reproducible(self):
        residuals, episodes = self._panel_with_planted_effect()
        config = _make_config()
        first = estimate_pair(residuals, "src", "tgt", episodes, config,
                              np.random.default_rng(config.random_seed))
        second = estimate_pair(residuals, "src", "tgt", episodes, config,
                               np.random.default_rng(config.random_seed))
        assert [e.as_dict() for e in first] == [e.as_dict() for e in second]

    def test_no_episodes_yields_insufficient_not_a_crash(self):
        residuals, _ = self._panel_with_planted_effect()
        empty = ShockEpisodes("src", SHOCK_SQUEEZE, [])
        effects = estimate_pair(residuals, "src", "tgt", empty, _make_config())
        assert all(e.status == STATUS_INSUFFICIENT for e in effects)
        assert all(e.n_episodes == 0 for e in effects)

    def test_unknown_target_raises(self):
        residuals, episodes = self._panel_with_planted_effect()
        with pytest.raises(KeyError):
            estimate_pair(residuals, "src", "nope", episodes, _make_config())

    def test_peak_prefers_significant_over_merely_large(self):
        effects = [
            HorizonEffect(1, 0.05, 0.01, 0.09, 0.0, 10, STATUS_SIGNIFICANT),
            HorizonEffect(2, 0.50, -0.4, 1.4, 0.0, 10, "INCONCLUSIVE"),
        ]
        assert peak_effect(effects).horizon == 1

    def test_peak_of_empty_is_none(self):
        assert peak_effect([]) is None


# ------------------------------------------------------------- the artifact


class TestMatrixArtifact:
    def _matrix(self):
        effects = [HorizonEffect(1, 0.1, 0.02, 0.18, 0.0, 12, STATUS_SIGNIFICANT, 0.01)]
        edge = SpilloverEdge(
            source="onion", target="tomato", shock_type=SHOCK_SQUEEZE,
            effects=effects, peak_horizon=1, peak_elasticity=0.1,
            status=STATUS_SIGNIFICANT, n_episodes=12, half_life_periods=1.5,
        )
        return SpilloverMatrix(
            edges=[edge], commodities=["onion", "tomato"],
            markets={"onion": "lasalgaon", "tomato": "kolar"},
            panel_hash="abc123", built_at="2026-01-01T00:00:00Z",
        )

    def test_round_trip_preserves_content(self, tmp_path):
        original = self._matrix()
        path = original.save(tmp_path / "m.json")
        loaded = SpilloverMatrix.load(path)
        assert loaded.to_dict() == original.to_dict()

    def test_save_is_atomic_and_leaves_no_temp_file(self, tmp_path):
        path = self._matrix().save(tmp_path / "m.json")
        assert path.exists()
        assert not list(tmp_path.glob("*.tmp"))

    def test_incompatible_schema_is_refused(self, tmp_path):
        path = tmp_path / "m.json"
        payload = self._matrix().to_dict()
        payload["schema_version"] = "99.0.0"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="Incompatible"):
            SpilloverMatrix.load(path)

    def test_current_schema_version_loads(self, tmp_path):
        path = self._matrix().save(tmp_path / "m.json")
        assert SpilloverMatrix.load(path).schema_version == SCHEMA_VERSION

    def test_downstream_filters_to_actionable_by_default(self):
        matrix = self._matrix()
        matrix.edges.append(
            SpilloverEdge(
                source="onion", target="potato", shock_type=SHOCK_SQUEEZE,
                effects=[], peak_horizon=None, peak_elasticity=None,
                status=STATUS_INSUFFICIENT, n_episodes=2,
            )
        )
        assert len(matrix.downstream("onion", SHOCK_SQUEEZE)) == 1
        assert len(matrix.downstream("onion", SHOCK_SQUEEZE, actionable_only=False)) == 2


# ---------------------------------------------------------- runtime service


class TestServiceFailsSafe:
    """The service must never be able to break a request path."""

    def test_missing_artifact_reports_unavailable(self, tmp_path):
        service = SpilloverService(artifact_path=tmp_path / "absent.json")
        assert service.is_available is False
        assert service.status()["available"] is False
        assert service.status()["reason"] == "artifact_not_built"

    def test_missing_artifact_queries_return_empty(self, tmp_path):
        service = SpilloverService(artifact_path=tmp_path / "absent.json")
        assert service.get_impacts("onion", SHOCK_SQUEEZE) == []
        assert service.get_edge("onion", "tomato", SHOCK_SQUEEZE) is None
        assert service.commodities() == []

    def test_corrupt_artifact_degrades_quietly(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{ not json", encoding="utf-8")
        service = SpilloverService(artifact_path=path)
        assert service.is_available is False
        assert service.get_impacts("onion", SHOCK_SQUEEZE) == []
        assert "unreadable" in service.status()["reason"]

    def test_malformed_arguments_do_not_raise(self, tmp_path):
        path = tmp_path / "absent.json"
        service = SpilloverService(artifact_path=path)
        assert service.get_impacts(None, None) == []
        assert service.get_impacts("", "") == []
        assert service.get_impacts("onion", "NOT_A_SHOCK") == []

    def test_inputs_are_normalised(self, tmp_path):
        edge = SpilloverEdge(
            source="onion", target="tomato", shock_type=SHOCK_SQUEEZE,
            effects=[HorizonEffect(1, 0.1, 0.02, 0.18, 0.0, 12, STATUS_SIGNIFICANT)],
            peak_horizon=1, peak_elasticity=0.1,
            status=STATUS_SIGNIFICANT, n_episodes=12,
        )
        matrix = SpilloverMatrix(edges=[edge], commodities=["onion", "tomato"])
        path = matrix.save(tmp_path / "m.json")
        service = SpilloverService(artifact_path=path)
        assert len(service.get_impacts("  ONION  ", "squeeze")) == 1

    def test_reload_picks_up_a_new_artifact(self, tmp_path):
        path = tmp_path / "m.json"
        service = SpilloverService(artifact_path=path)
        assert service.is_available is False

        SpilloverMatrix(edges=[], commodities=["onion"]).save(path)
        assert service.reload() is True
        assert service.is_available is True


# ------------------------------------------------- topology integration guard


class TestTopologyIntegration:
    def test_declared_topology_still_works_without_learned_edges(self):
        from mandisense_ai.cognition.world_model.topology import MarketTopology

        topology = MarketTopology(load_learned_spillover=False)
        assert topology.spillover_source == "declared"
        substitutes = [e for e in topology.edges if e.relationship == "substitutes"]
        assert len(substitutes) == 1
        assert substitutes[0].origin == "declared"

    def test_mandi_propagation_is_unaffected_by_spillover(self):
        """Commodity edges must not leak into mandi corridor propagation."""
        from mandisense_ai.cognition.world_model.topology import MarketTopology

        declared = MarketTopology(load_learned_spillover=False)
        learned = MarketTopology(load_learned_spillover=True)

        def mandi_edges(topology):
            return sorted(
                (e.source, e.target, e.weight, e.latency_hours)
                for e in topology.edges
                if e.relationship == "influences"
            )

        assert mandi_edges(declared) == mandi_edges(learned)

    def test_topology_construction_survives_a_broken_service(self, monkeypatch):
        from mandisense_ai.cognition.world_model import topology as topology_module

        def explode():
            raise RuntimeError("service is down")

        monkeypatch.setattr(
            "mandisense_ai.spillover.service.get_spillover_service", explode
        )
        built = topology_module.MarketTopology(load_learned_spillover=True)
        assert built.spillover_source == "declared"
        assert len(built.edges) > 0


# ------------------------------------------------- placebo gating (end to end)


class TestPlaceboGating:
    """
    A failed permutation placebo invalidates the pipeline as a whole. No path
    through the system may surface an edge as actionable after that, however
    convincing the individual edge looks.
    """

    def _matrix_with_verdict(self, verdict):
        effects = [HorizonEffect(1, 0.25, 0.10, 0.40, 0.0, 20, STATUS_SIGNIFICANT, 0.001)]
        edge = SpilloverEdge(
            source="onion", target="tomato", shock_type=SHOCK_SQUEEZE,
            effects=effects, peak_horizon=1, peak_elasticity=0.25,
            status=STATUS_SIGNIFICANT, n_episodes=20,
        )
        return SpilloverMatrix(
            edges=[edge],
            commodities=["onion", "tomato"],
            diagnostics={"placebo": {"verdict": verdict}} if verdict else {},
        )

    def test_failed_placebo_suppresses_actionable_edges(self):
        matrix = self._matrix_with_verdict("FAIL")
        assert matrix.edges[0].is_actionable is True  # the edge itself looks fine
        assert matrix.actionable_edges == []          # but the pipeline did not
        assert matrix.is_validated is False

    def test_passed_placebo_allows_actionable_edges(self):
        matrix = self._matrix_with_verdict("PASS")
        assert len(matrix.actionable_edges) == 1
        assert matrix.is_validated is True

    def test_absent_placebo_is_not_treated_as_a_pass(self):
        matrix = self._matrix_with_verdict(None)
        assert matrix.placebo_verdict is None
        assert matrix.is_validated is False

    def test_service_refuses_to_serve_edges_after_a_failed_placebo(self, tmp_path):
        path = self._matrix_with_verdict("FAIL").save(tmp_path / "m.json")
        service = SpilloverService(artifact_path=path)
        assert service.get_impacts("onion", SHOCK_SQUEEZE) == []
        # The evidence stays inspectable for anyone who asks for it explicitly.
        assert len(service.get_impacts("onion", SHOCK_SQUEEZE, actionable_only=False)) == 1

    def test_topology_ignores_edges_from_a_failed_pipeline(self, tmp_path, monkeypatch):
        from mandisense_ai.cognition.world_model.topology import MarketTopology

        path = self._matrix_with_verdict("FAIL").save(tmp_path / "m.json")
        service = SpilloverService(artifact_path=path)
        monkeypatch.setattr(
            "mandisense_ai.spillover.service.get_spillover_service", lambda: service
        )
        topology = MarketTopology(load_learned_spillover=True)
        assert topology.spillover_source == "declared"
        assert all(e.origin == "declared" for e in topology.edges)

    def test_topology_adopts_edges_from_a_validated_pipeline(self, tmp_path, monkeypatch):
        from mandisense_ai.cognition.world_model.topology import MarketTopology

        path = self._matrix_with_verdict("PASS").save(tmp_path / "m.json")
        service = SpilloverService(artifact_path=path)
        monkeypatch.setattr(
            "mandisense_ai.spillover.service.get_spillover_service", lambda: service
        )
        topology = MarketTopology(load_learned_spillover=True)
        assert topology.spillover_source == "learned"
        learned = [e for e in topology.edges if e.origin == "learned"]
        assert len(learned) == 1
        assert learned[0].source == "onion" and learned[0].target == "tomato"
