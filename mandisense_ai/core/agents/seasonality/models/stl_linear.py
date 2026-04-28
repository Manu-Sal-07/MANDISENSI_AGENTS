"""
STL + Linear Regression Seasonality Model.

Strategy:
  1. Fit a Seasonal-Trend decomposition using LOESS (STL) on training prices.
  2. Separate the training target into (trend + residual) — remove seasonal.
  3. Train a LinearRegression on the provided feature matrix X against that
     de-seasonalised target.
  4. At predict time, add the most-recent seasonal value back as an offset.

Why this model?
  STL reliably extracts a mandi-specific seasonal curve even when festivals
  or harvest spikes cause heavy outliers (robust=True).  The residual linear
  layer captures exogenous signals (arrivals, lags, momentum).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.seasonal import STL

from core.agents.seasonality.models.base import BaseSeasonalityModel
from utils.logger import get_logger

logger = get_logger(__name__)

# Minimum rows needed to run STL (needs at least 2 full periods of the chosen
# period length).  Below this we fall back to a plain LinearRegression.
_MIN_STL_ROWS = 730   # ~2 years of daily data


class STLLinearRegressionModel(BaseSeasonalityModel):
    """
    STL decomposition + Linear Regression hybrid.

    The seasonal offset extracted from STL is stored after training and added
    back as a constant correction to all future predictions.  This works well
    for short-horizon (≤ 30 day) forecasts where the seasonal component is
    effectively stationary within a single season window.
    """

    model_name = "STLLinearRegression"

    def __init__(self, stl_period: int = 365, seasonal_window: int = 21):
        self._stl_period = stl_period
        self._seasonal_window = seasonal_window if seasonal_window % 2 == 1 else seasonal_window + 1
        self._lr = LinearRegression()
        self._seasonal_offset: float = 0.0
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "STLLinearRegressionModel":
        prices = y.values.astype(float)

        if len(prices) >= _MIN_STL_ROWS:
            try:
                # Use log1p to stabilise multiplicative seasonality
                log_prices = np.log1p(prices)
                period = min(self._stl_period, len(prices) // 2)
                stl = STL(log_prices, period=period,
                          seasonal=self._seasonal_window, robust=True)
                res = stl.fit()

                seasonal = res.seasonal
                # De-seasonalise: target becomes trend + residual
                deseasonalised = log_prices - seasonal
                self._seasonal_offset = float(seasonal[-1])   # carry last value
                y_train = pd.Series(deseasonalised, index=y.index)
                logger.info(f"[{self.model_name}] STL fit OK – period={period}, "
                            f"seasonal_offset={self._seasonal_offset:.4f}")
            except Exception as exc:
                logger.warning(f"[{self.model_name}] STL failed ({exc}); "
                               "falling back to raw log-prices.")
                y_train = pd.Series(np.log1p(prices), index=y.index)
                self._seasonal_offset = 0.0
        else:
            logger.info(f"[{self.model_name}] Insufficient rows for STL "
                        f"({len(prices)} < {_MIN_STL_ROWS}); using log(price) directly.")
            y_train = pd.Series(np.log1p(prices), index=y.index)
            self._seasonal_offset = 0.0

        self._lr.fit(X.fillna(0), y_train)
        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")
        log_preds = self._lr.predict(X.fillna(0)) + self._seasonal_offset
        # Inverse log1p to return prices on original scale
        return np.expm1(log_preds)
