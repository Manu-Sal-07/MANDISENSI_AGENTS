"""The specialist-agent council: weight learning, the promotion rule, the read side and the traced run."""

import numpy as np
import pytest

from mandisense_ai.forecasting import council, council_service, trace
from mandisense_ai.forecasting.config import DEFAULT_CONFIG


def test_every_feature_belongs_to_exactly_one_agent():
    from mandisense_ai.forecasting.train import _prepare_training_frame  # noqa: F401  (feature list is read from the saved bundle below)
    import joblib
    from mandisense_ai.forecasting.train import ForecastBundle

    features = ForecastBundle.load().features
    cols = council.agent_columns(features)
    owned = [c for name, cs in cols.items() for c in cs if c not in council.SHARED]
    assert sorted(owned) == sorted(c for c in features if c not in council.SHARED)       # no feature unowned or owned twice
    assert all(set(council.SHARED) <= set(cs) for cs in cols.values())


def test_unowned_feature_is_refused():
    with pytest.raises(ValueError):
        council.agent_columns(["month", "a_feature_no_agent_owns"])


def test_nnls_weights_are_non_negative_and_recover_a_known_mixture():
    rng = np.random.default_rng(0)
    P = rng.normal(size=(400, 3))
    y = 0.6 * P[:, 0] + 0.3 * P[:, 2]
    w = council.nnls_weights(P, y)
    assert (w >= 0).all() and np.allclose(w, [0.6, 0.0, 0.3], atol=1e-6)


def test_constrained_weights_never_amplify_the_agents():
    assert council.constrain(np.array([1.2, 0.8, 1.0])).sum() == pytest.approx(1.0)
    small = np.array([0.1, 0.2, 0.0])
    assert np.array_equal(council.constrain(small), small)             # already shrunk: left alone
    assert council.constrain(np.array([2.0, 0.0])).max() <= 1.0


def _summary(a_better: bool, folds_won: int, folds: int = 4):
    return {"council_vs_single": {"a_better": a_better}, "folds_council_beats_single": folds_won, "folds": folds}


def test_promotion_needs_both_significance_and_consistency():
    assert council.promote(_summary(True, 4)) and council.promote(_summary(True, 3))
    assert not council.promote(_summary(True, 2))               # significant overall but wins too few folds
    assert not council.promote(_summary(False, 4))              # wins folds but the interval does not exclude zero


def test_learned_weights_use_only_the_earlier_part_of_the_window():
    import pandas as pd

    n = 600
    frame = pd.DataFrame({"date": pd.date_range("2022-01-01", periods=n), "x": np.random.default_rng(1).normal(size=n)})
    frame["y"] = 0.5 * frame["x"]
    seen = {}
    real = council._fit_agents

    def spy(train, cols, target, config):
        seen["last_train_date"] = train["date"].max()
        return real(train, cols, target, config)

    council._fit_agents = spy
    try:
        council.learn_weights(frame, {"a": ["x"]}, "y", DEFAULT_CONFIG)
    finally:
        council._fit_agents = real
    assert seen["last_train_date"] <= frame["date"].quantile(council.INNER_SHARE)


@pytest.mark.skipif(not (council.OUT_DIR / "forecasts.json").exists(), reason="council not built (scripts/eval_agent_council.py)")
class TestBuiltCouncil:
    def test_view_carries_each_agent_and_the_verdict(self):
        v = council_service.view("tomato", "kolar_apmc")
        assert v["status"] == "OK" and set(v["agents"]) == set(council.AGENT_FEATURES)
        for h in v["horizons"].values():
            assert set(h["agents"]) == set(v["agents"]) and isinstance(h["promoted"], bool)
            assert sum(h["weights"].values()) <= 1.0 + 1e-6, "served weights must never amplify"

    def test_unknown_series_is_refused_not_invented(self):
        assert council_service.view("tomato", "no_such_apmc")["status"] == "UNAVAILABLE"

    def test_legacy_mandi_spelling_resolves(self):
        assert council_service.view("onion", "bangalore_apmc")["status"] == "OK"

    def test_trace_runs_end_to_end_with_ordered_events(self):
        events = trace.collect("tomato", "kolar")
        steps = [e["step"] for e in events]
        assert steps[0] == "query_received" and steps[-1] == "final_output"
        assert steps.count("agent_completed") == len(council.AGENT_FEATURES) and "meta_ensemble_completed" in steps
        assert "external_completed" in steps

    def test_evaluation_states_its_promotion_rule(self):
        ev = council_service.evaluation()
        assert ev["status"] == "OK" and "promote" in ev["rule"] and set(ev["horizons"]) == {"3", "5", "7"}
