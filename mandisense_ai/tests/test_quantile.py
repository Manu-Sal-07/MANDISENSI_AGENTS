"""
Tests for row-conditional prediction intervals.

Organised around the properties that separate this from the flat
pooled-residual band it sits alongside:

  * predicted quantiles are monotone per row even when the raw model output
    is not (the defensive sort in `predict_quantiles` is not decoration)
  * the band this produces is measurably a function of the row, not just of
    which fold or evaluation window the row happened to fall in
  * a bad or miscalibrated fit degrades to `None`s rather than a wrong number
  * unpromoted or missing quantile models fall back to the existing,
    already-validated pooled-residual band rather than serving nothing
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.quantile import (
    QUANTILE_LEVELS,
    _make_quantile_estimator,
    predict_quantiles,
    quantile_price_interval,
    train_quantile_models,
)


def _config(**overrides):
    base = dict(horizons=(1, 3), min_train_rows=40, walk_forward_folds=2)
    base.update(overrides)
    return ForecastConfig(**base)


def _synthetic_frame(n=400, seed=3):
    """A frame shaped like `_prepare_training_frame`'s output: feature columns
    plus `y_h{horizon}` targets, with volatility that genuinely varies by row
    so a row-conditional model has something real to key off."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    volatility_regime = rng.integers(0, 2, n).astype(float)  # 0=calm, 1=volatile
    momentum = rng.normal(0, 1, n)
    noise_scale = 0.01 + volatility_regime * 0.08
    y1 = momentum * 0.02 + rng.normal(0, 1, n) * noise_scale
    y3 = momentum * 0.03 + rng.normal(0, 1, n) * noise_scale * 1.5

    return pd.DataFrame(
        {
            "date": dates,
            "commodity": "tomato",
            "mandi_id": "kolar_apmc",
            "modal_price": 1000.0,
            "momentum": momentum,
            "volatility_regime": volatility_regime,
            "y_h1": y1,
            "y_h3": y3,
        }
    )


FEATURES = ["momentum", "volatility_regime"]


class TestMonotonicity:
    def test_predicted_quantiles_are_never_crossed(self):
        """The defensive sort in `predict_quantiles` — without it a noisy fit
        can produce a p75 below its own p25 on some rows, which is not a
        merely cosmetic problem: it would invert the reported interval."""
        frame = _synthetic_frame()
        model = _make_quantile_estimator(_config(), QUANTILE_LEVELS)
        model.fit(frame[FEATURES], frame["y_h1"])

        predicted = predict_quantiles(model, frame[FEATURES], QUANTILE_LEVELS)
        matrix = np.column_stack([predicted[f"{level:g}"] for level in QUANTILE_LEVELS])

        assert np.all(np.diff(matrix, axis=1) >= 0)

    def test_handles_a_single_row(self):
        frame = _synthetic_frame(n=60)
        model = _make_quantile_estimator(_config(), QUANTILE_LEVELS)
        model.fit(frame[FEATURES], frame["y_h1"])

        predicted = predict_quantiles(model, frame[FEATURES].iloc[[0]], QUANTILE_LEVELS)
        values = [predicted[f"{level:g}"][0] for level in QUANTILE_LEVELS]
        assert values == sorted(values)


class TestRowConditionality:
    """The property that distinguishes this from a flat band: width should
    actually vary with the row's own volatility signal."""

    def test_band_is_wider_for_rows_flagged_as_volatile(self):
        frame = _synthetic_frame(n=600)
        model = _make_quantile_estimator(_config(), QUANTILE_LEVELS)
        model.fit(frame[FEATURES], frame["y_h1"])

        calm = frame[frame["volatility_regime"] == 0]
        volatile = frame[frame["volatility_regime"] == 1]

        calm_pred = predict_quantiles(model, calm[FEATURES], QUANTILE_LEVELS)
        volatile_pred = predict_quantiles(model, volatile[FEATURES], QUANTILE_LEVELS)

        calm_width = np.mean(calm_pred["0.95"] - calm_pred["0.05"])
        volatile_width = np.mean(volatile_pred["0.95"] - volatile_pred["0.05"])

        assert volatile_width > calm_width

    def test_width_varies_across_rows_within_a_single_batch(self):
        """A flat pooled-residual band has ~zero width variance across rows in
        the same evaluation window by construction (the offset is a single
        pair of numbers applied to every row). This model's band should not."""
        frame = _synthetic_frame(n=600)
        model = _make_quantile_estimator(_config(), QUANTILE_LEVELS)
        model.fit(frame[FEATURES], frame["y_h1"])

        predicted = predict_quantiles(model, frame[FEATURES], QUANTILE_LEVELS)
        widths = predicted["0.95"] - predicted["0.05"]

        assert np.std(widths) > 1e-4


class TestTrainQuantileModels:
    def test_trains_one_model_per_configured_horizon(self):
        frame = _synthetic_frame(n=300)
        models = train_quantile_models(frame, FEATURES, _config(horizons=(1, 3)))
        assert set(models.keys()) == {1, 3}

    def test_skips_a_horizon_with_too_few_rows(self):
        frame = _synthetic_frame(n=300)
        frame.loc[frame.index[:-10], "y_h3"] = np.nan  # only 10 usable rows left
        models = train_quantile_models(
            frame, FEATURES, _config(horizons=(1, 3), min_train_rows=40)
        )
        assert 1 in models
        assert 3 not in models


class TestPriceIntervalConversion:
    def test_converts_log_return_quantiles_to_a_price_band(self):
        quantiles = {"0.05": -0.10, "0.25": -0.02, "0.75": 0.02, "0.95": 0.10}
        interval = quantile_price_interval(quantiles, base_price=1000.0)

        assert interval["p05"] < interval["p25"] < interval["p75"] < interval["p95"]
        assert interval["p05"] == pytest.approx(1000.0 * np.exp(-0.10), abs=0.01)
        assert interval["p95"] == pytest.approx(1000.0 * np.exp(0.10), abs=0.01)

    def test_missing_quantile_degrades_to_all_none(self):
        """A partial result is not a usable interval — reporting three real
        numbers and one None would look like a band with a missing edge
        rather than what it is, a failed prediction."""
        quantiles = {"0.05": -0.10, "0.25": -0.02, "0.75": 0.02}  # 0.95 missing
        interval = quantile_price_interval(quantiles, base_price=1000.0)

        assert interval == {"p05": None, "p25": None, "p75": None, "p95": None}
