"""
Tests for AgentEnsemble (Stack A's shared walk-forward CV / weighting engine).

There was no test of this class at all before this file: `agent_ensemble.py`
is exercised only through `train_arrival_models.py`, which nothing in this
suite calls either. That mattered concretely once its internal metric keys
were renamed from the historically mislabelled `avg_mape`/`fest_mape`/
`fold_mapes` (the values were always mean absolute error, not MAPE — see the
module's own comments) to `avg_mae`/`fest_mae`/`fold_maes`: a typo in that
rename would have raised a `KeyError` on the very first `fit()` call, and
nothing would have caught it before this file existed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from mandisense_ai.ensemble.agent_ensemble import AgentEnsemble


def _linear_data(n=300, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    y = pd.Series(X["a"] * 2 - X["b"] + rng.normal(scale=0.3, size=n))
    regime = pd.Series(rng.integers(0, 2, n))
    return X, y, regime


class TestFitProducesUsableState:
    def test_weights_sum_to_one(self):
        X, y, regime = _linear_data()
        ensemble = AgentEnsemble(
            models={"ridge_a": Ridge(alpha=1.0), "ridge_b": Ridge(alpha=10.0)},
            n_splits=3,
        )
        ensemble.fit(X, y, regime_flags=regime)

        assert ensemble.weights
        assert sum(ensemble.weights.values()) == pytest.approx(1.0, abs=1e-6)

    def test_errors_are_plain_finite_numbers(self):
        """The property the rename exists to guarantee: no KeyError reaching
        into `cv_results`, and no residue of the old mislabelled keys."""
        X, y, regime = _linear_data()
        ensemble = AgentEnsemble(models={"ridge": Ridge()}, n_splits=3)
        ensemble.fit(X, y, regime_flags=regime)

        assert set(ensemble.errors.keys()) == {"ridge"}
        assert np.isfinite(ensemble.errors["ridge"])
        assert ensemble.errors["ridge"] >= 0

    def test_better_model_gets_more_weight(self):
        """A model whose regularisation is closer to the true (near-zero
        noise) relationship should end up with the larger weight — the
        inverse-error weighting has to actually favour accuracy."""
        rng = np.random.default_rng(1)
        n = 400
        X = pd.DataFrame({"a": rng.normal(size=n)})
        y = pd.Series(X["a"] * 3 + rng.normal(scale=0.05, size=n))

        ensemble = AgentEnsemble(
            models={"light_reg": Ridge(alpha=0.01), "heavy_reg": Ridge(alpha=500.0)},
            n_splits=4,
        )
        ensemble.fit(X, y)

        assert ensemble.weights["light_reg"] > ensemble.weights["heavy_reg"]
        assert ensemble.best_model_name == "light_reg"

    def test_predict_before_fit_raises(self):
        ensemble = AgentEnsemble(models={"ridge": Ridge()})
        with pytest.raises(RuntimeError):
            ensemble.predict(pd.DataFrame({"a": [0.0]}))


class TestPredictAndLog:
    def test_predict_returns_one_value_per_row(self):
        X, y, regime = _linear_data()
        ensemble = AgentEnsemble(models={"ridge": Ridge()}, n_splits=3)
        ensemble.fit(X, y, regime_flags=regime)

        preds = ensemble.predict(X.iloc[:7])
        assert len(preds) == 7
        assert np.all(np.isfinite(preds))

    def test_ensemble_log_exposes_renamed_fields_not_the_old_ones(self):
        X, y, regime = _linear_data()
        ensemble = AgentEnsemble(models={"ridge": Ridge()}, n_splits=3)
        ensemble.fit(X, y, regime_flags=regime)
        ensemble.predict(X.iloc[:3])

        log = ensemble.get_ensemble_log()
        assert "model_errors" in log
        assert "model_cv_fold_errors" in log
        assert set(log["model_errors"].keys()) == {"ridge"}
        assert isinstance(log["ranked_models"], list)

    def test_log_before_fit_reports_unfitted_rather_than_raising(self):
        ensemble = AgentEnsemble(models={"ridge": Ridge()})
        log = ensemble.get_ensemble_log()
        assert log["status"] == "unfitted"


class TestMinWeightPruning:
    def test_a_much_worse_model_is_dropped_below_threshold(self):
        rng = np.random.default_rng(2)
        n = 400
        X = pd.DataFrame({"a": rng.normal(size=n)})
        y = pd.Series(X["a"] * 5 + rng.normal(scale=0.02, size=n))

        class ConstantModel:
            def fit(self, X, y):
                return self

            def predict(self, X):
                return np.zeros(len(X))

        ensemble = AgentEnsemble(
            models={"good": Ridge(alpha=0.01), "useless": ConstantModel()},
            n_splits=3,
            min_weight_threshold=0.05,
        )
        ensemble.fit(X, y)

        assert "useless" not in ensemble.weights
        assert ensemble.weights.get("good") == pytest.approx(1.0, abs=1e-6)
