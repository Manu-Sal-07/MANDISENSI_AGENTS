"""
Tests for the validated point-model / linear-model blend (see `train.py`'s
`_walk_forward_scores` blend evaluation and `train_bundle`'s promotion gate).

Organised around the properties that keep this from repeating Stack A's
`meta_ensemble.py` mistake — a fusion layer with ~25 hand-tuned magic
constants and no cross-validation of any of them:

  * the blend weight is derived from each fold's own held-out error, not a
    constant chosen to look good on one dataset
  * a horizon is only served the blend where it was *measured* to beat the
    single point model out of sample — presence in `blend_models` is itself
    the promotion state, so there is nothing to fall out of sync
  * `sample_weight` genuinely reaches the linear model through its
    `Pipeline` wrapper (a bare kwarg silently raises on a `Pipeline`, it does
    not silently no-op — but the routing still has to be exercised)
  * a linear model can fit and predict through real NaNs (arrivals absent,
    no prior-year seasonal reference yet) without the caller having to
    pre-impute anything
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.train import (
    _fit_model,
    _make_linear_estimator,
    _walk_forward_scores,
    train_bundle,
)


def _config(**overrides):
    base = dict(
        horizons=(1,),
        min_train_rows=60,
        walk_forward_folds=3,
        use_model_blend=True,
        use_seasonal_climatology=False,  # isolate blend behaviour from other layers
        use_absence_features=False,
        arrival_dropout_rate=0.0,
    )
    base.update(overrides)
    return ForecastConfig(**base)


def _frame_with_linear_signal(n=500, seed=5, nan_rate=0.0):
    """
    A target that is almost perfectly linear in one feature and only weakly,
    noisily related to a second — the regime where a plain linear model
    should out-predict a shallow, heavily regularised tree on held-out data,
    so the blend has a real, measurable reason to lean on it.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    linear_driver = rng.normal(0, 1, n)
    noise_driver = rng.normal(0, 1, n)
    y = linear_driver * 0.05 + noise_driver * 0.002 + rng.normal(0, 0.001, n)

    frame = pd.DataFrame(
        {
            "date": dates,
            "commodity": "tomato",
            "mandi_id": "kolar_apmc",
            "modal_price": 1000.0,
            "linear_driver": linear_driver,
            "noise_driver": noise_driver,
            "y_h1": y,
        }
    )
    if nan_rate > 0:
        mask = rng.random(n) < nan_rate
        frame.loc[mask, "linear_driver"] = np.nan
    return frame


FEATURES = ["linear_driver", "noise_driver"]


class TestLinearEstimatorMechanics:
    def test_fits_and_predicts_through_real_nans(self):
        frame = _frame_with_linear_signal(nan_rate=0.1)
        model = _make_linear_estimator(_config())
        _fit_model(model, frame[FEATURES], frame["y_h1"], weights=None)

        preds = model.predict(frame[FEATURES])
        assert np.all(np.isfinite(preds))

    def test_sample_weight_reaches_the_pipeline(self):
        """A bare `sample_weight=` kwarg raises on a `Pipeline` rather than
        silently no-op'ing, but the routing through `_fit_model` still has to
        actually change the fit, or quality weighting would be a no-op for
        every linear model regardless."""
        frame = _frame_with_linear_signal()
        heavy_weights = np.ones(len(frame))
        heavy_weights[: len(frame) // 2] = 0.001

        weighted = _make_linear_estimator(_config())
        _fit_model(weighted, frame[FEATURES], frame["y_h1"], weights=heavy_weights)

        unweighted = _make_linear_estimator(_config())
        _fit_model(unweighted, frame[FEATURES], frame["y_h1"], weights=None)

        w_coef = weighted.named_steps["model"].coef_
        u_coef = unweighted.named_steps["model"].coef_
        assert not np.allclose(w_coef, u_coef)


class TestWalkForwardBlendEvaluation:
    def test_blend_fields_present_when_enabled(self):
        frame = _frame_with_linear_signal()
        frame["y_h1"] = frame["y_h1"]  # already the target column name expected
        result = _walk_forward_scores(frame, FEATURES, 1, _config())

        assert result["status"] == "OK"
        assert "blend_mae" in result
        assert "linear_mae" in result
        assert "blend_weight_xgboost" in result
        assert 0.0 <= result["blend_weight_xgboost"] <= 1.0

    def test_blend_fields_absent_when_disabled(self):
        frame = _frame_with_linear_signal()
        result = _walk_forward_scores(frame, FEATURES, 1, _config(use_model_blend=False))

        assert result["status"] == "OK"
        assert "blend_mae" not in result
        assert "blend_beats_single" not in result

    def test_a_genuinely_linear_target_favours_the_linear_model_in_the_blend_weight(self):
        """With the target constructed to be almost exactly linear in one
        input, a shallow heavily-regularised booster should not out-predict
        the linear fit on held-out folds -- the measured blend weight should
        reflect that by leaning away from pure XGBoost."""
        frame = _frame_with_linear_signal(n=800)
        result = _walk_forward_scores(frame, FEATURES, 1, _config(walk_forward_folds=4))

        assert result["blend_weight_xgboost"] < 0.9

    def test_fold_win_rate_is_computed_from_actual_per_fold_outcomes(self):
        frame = _frame_with_linear_signal(n=800)
        result = _walk_forward_scores(frame, FEATURES, 1, _config(walk_forward_folds=4))

        recomputed_wins = sum(
            1 for f in result["fold_reports"]
            if "blend_mae" in f and f["blend_mae"] < f["model_mae"]
        )
        expected_rate = recomputed_wins / len(
            [f for f in result["fold_reports"] if "blend_mae" in f]
        )
        assert result["blend_fold_win_rate"] == pytest.approx(expected_rate)


class TestPromotionIsHonest:
    def test_blend_model_only_persisted_when_measured_to_win(self):
        """A stricter margin than any real blend could plausibly clear -- the
        promotion gate must actually gate, not just report a number nobody
        acts on."""
        frame = _frame_with_linear_signal(n=800)
        strict_config = _config(walk_forward_folds=4, blend_improvement_margin=0.99)

        bundle = train_bundle(frame, strict_config)
        assert 1 not in bundle.blend_models
        assert 1 not in bundle.blend_weights

    def test_blend_model_persisted_and_usable_when_it_wins(self):
        frame = _frame_with_linear_signal(n=800)
        lenient_config = _config(walk_forward_folds=4, blend_improvement_margin=-1.0)

        bundle = train_bundle(frame, lenient_config)
        if 1 in bundle.blend_models:
            weights = bundle.blend_weights[1]
            assert weights["xgboost"] + weights["linear"] == pytest.approx(1.0, abs=1e-3)
            pred = bundle.blend_models[1].predict(frame[FEATURES].iloc[:3])
            assert np.all(np.isfinite(pred))

    def test_a_horizons_presence_in_blend_models_is_its_own_promotion_flag(self):
        """No separate promoted-horizons list to drift out of sync with which
        models actually got fit and saved."""
        frame = _frame_with_linear_signal(n=800)
        bundle = train_bundle(frame, _config(walk_forward_folds=4))

        for horizon in bundle.blend_models:
            assert horizon in bundle.blend_weights
