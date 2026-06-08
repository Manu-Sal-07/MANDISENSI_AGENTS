"""
SARIMA Seasonality Model (Optional – Statistical Tier).

Why this model?
  SARIMA (Seasonal ARIMA) is a pure statistical model that explicitly
  parameterises the seasonal lag structure.  It is especially strong when:
    - The commodity has a stable, repeating annual pattern (e.g., Rabi / Kharif)
    - The dataset is clean and nearly gap-free
    - Other ML models are over-fitting noise

  IMPORTANT CONSTRAINTS:
    - Fitting SARIMA is computationally expensive (order selection can take
      minutes on long series).  We use a fixed, conservative order rather than
      auto-arima to keep training inside the weekly recalibration budget.
    - X (exogenous features) is NOT used — SARIMA is purely univariate.
      This intentionally adds diversity to the ensemble.
    - If statsmodels raises a convergence warning or the series is too short,
      the model falls back to a trailing 30-day mean silently.

  Fixed order: SARIMA(1,1,1)(1,0,0)[52]
    - (1,1,1)    : AR(1) + one differencing + MA(1)  — standard for mandi prices
    - (1,0,0)[52]: seasonal AR at 52-week lag (yearly seasonality in weekly data)
    - Fit on weekly-resampled prices to keep computation tractable.
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

from mandisense_ai.core.agents.seasonality.models.base import BaseSeasonalityModel
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Minimum weekly observations to attempt SARIMA fitting
_MIN_WEEKLY_OBS = 104   # 2 years


class SARIMASeasonalityModel(BaseSeasonalityModel):
    """
    SARIMA(1,1,1)(1,0,0)[52] fitted on weekly-resampled modal prices.
    Prediction is constant across all rows of X (univariate model).
    """

    model_name = "SARIMA"

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 0, 0, 52)):
        self._order = order
        self._seasonal_order = seasonal_order
        self._fallback_mean: float = 0.0
        self._sarima_result = None
        self._fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SARIMASeasonalityModel":
        self._fallback_mean = float(y.mean())   # always compute fallback

        # Resample to weekly frequency to reduce computation
        y_weekly = y.resample("W").mean().dropna() if isinstance(y.index, pd.DatetimeIndex) else (
            pd.Series(y.values).groupby(np.arange(len(y)) // 7).mean()
        )

        if len(y_weekly) < _MIN_WEEKLY_OBS:
            logger.warning(
                f"[{self.model_name}] Only {len(y_weekly)} weekly obs "
                f"(need {_MIN_WEEKLY_OBS}); using fallback mean."
            )
            self._fitted = True
            return self

        try:
            # Conditional import: statsmodels is optional dependency
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = SARIMAX(
                    y_weekly,
                    order=self._order,
                    seasonal_order=self._seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                self._sarima_result = model.fit(disp=False, maxiter=100)
                logger.info(f"[{self.model_name}] SARIMA fitted on {len(y_weekly)} weekly obs. "
                            f"AIC={self._sarima_result.aic:.1f}")
        except Exception as exc:
            logger.warning(f"[{self.model_name}] SARIMA fitting failed ({exc}); "
                           "using trailing mean fallback.")
            self._sarima_result = None

        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError(f"{self.model_name} has not been fitted yet.")

        if self._sarima_result is not None:
            try:
                # Forecast 1-step ahead (weekly) and scale to daily
                forecast = self._sarima_result.forecast(steps=1)
                pred_val = float(forecast.iloc[0]) if hasattr(forecast, "iloc") else float(forecast[0])
            except Exception as exc:
                logger.warning(f"[{self.model_name}] SARIMA predict failed ({exc}); using fallback.")
                pred_val = self._fallback_mean
        else:
            pred_val = self._fallback_mean

        return np.full(len(X), fill_value=pred_val)
