"""
EGARCH(1,1) Volatility Estimator for Agricultural Commodity Prices.

Captures volatility clustering and leverage effects in highly volatile mandi
price data.  Uses the ``arch`` library's EGARCH specification which:
  - Models the *log* of conditional variance → prevents negative variance
  - Captures asymmetric impact (bad news → higher volatility increase)
  - Is numerically more stable for fat-tailed commodity returns

Performance targets:
  - Full fit on 3,597 records: <5 s
  - 1-day forecast generation:  <100 ms
  - Memory footprint:           <50 MB
"""

from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from arch import arch_model
from arch.univariate.base import ARCHModelResult

try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)

# Suppress convergence warnings from arch that are non-critical in rolling fits
warnings.filterwarnings("ignore", category=RuntimeWarning, module="arch")


class GARCHVolatilityEstimator:
    """
    EGARCH(1,1) volatility estimator for agricultural commodity prices.

    Parameters
    ----------
    returns_series : pd.Series
        Daily log-returns or percentage returns with a DatetimeIndex.
    window : int
        Rolling window size for model fitting (default 252 trading days).

    Attributes
    ----------
    model : arch_model
        The arch_model specification (set after ``fit()``).
    fitted_results : ARCHModelResult
        Fitted model results (set after ``fit()``).
    """

    def __init__(self, returns_series: pd.Series, window: int = 252):
        if len(returns_series) < window:
            logger.warning(
                f"[GARCHEstimator] Series length ({len(returns_series)}) < "
                f"window ({window}).  Will use full series for fitting."
            )
        self.returns = returns_series.dropna().copy()
        self.window = window
        self.model: Optional[arch_model] = None
        self.fitted_results: Optional[ARCHModelResult] = None

    # ------------------------------------------------------------------ #
    #  Core fitting                                                       #
    # ------------------------------------------------------------------ #
    def fit(self) -> ARCHModelResult:
        """
        Fit EGARCH(1,1) model on the full historical returns series.

        Returns
        -------
        ARCHModelResult
            Fitted model result object.

        Raises
        ------
        RuntimeError
            If the optimiser fails to converge.
        """
        logger.info(
            f"[GARCHEstimator] Fitting EGARCH(1,1) on {len(self.returns)} observations"
        )

        # Scale returns to percentage for numerical stability
        scaled = self.returns * 100

        self.model = arch_model(
            scaled,
            vol="EGARCH",
            p=1,
            q=1,
            dist="normal",
        )

        try:
            self.fitted_results = self.model.fit(
                disp="off",
                show_warning=False,
            )
        except Exception as exc:
            logger.error(f"[GARCHEstimator] EGARCH fit failed: {exc}")
            raise RuntimeError(f"EGARCH fit failed: {exc}") from exc

        # Log key parameters
        params = self.fitted_results.params
        logger.info(
            f"[GARCHEstimator] Fit complete — "
            f"LL={self.fitted_results.loglikelihood:.2f}, "
            f"params={dict(params.round(4))}"
        )

        return self.fitted_results

    # ------------------------------------------------------------------ #
    #  Forecasting                                                        #
    # ------------------------------------------------------------------ #
    def forecast_volatility(self, horizon: int = 1) -> float:
        """
        Generate conditional variance forecast.

        Parameters
        ----------
        horizon : int
            Forecast horizon in days (default 1).

        Returns
        -------
        float
            Forecasted daily volatility (as a decimal, not percentage).

        Raises
        ------
        ValueError
            If the model has not been fitted.
        """
        if self.fitted_results is None:
            raise ValueError("Model must be fitted before forecasting.  Call fit() first.")

        forecast = self.fitted_results.forecast(horizon=horizon)
        conditional_variance = forecast.variance.values[-1, 0]

        # Convert from percentage-scaled variance back to decimal volatility
        daily_vol = np.sqrt(conditional_variance) / 100.0

        # Clip to sane bounds [0.001, 10.0]
        daily_vol = float(np.clip(daily_vol, 0.001, 10.0))

        return daily_vol

    def forecast_volatility_annualised(self, horizon: int = 1) -> float:
        """
        Annualised volatility forecast (√252 scaling).

        Parameters
        ----------
        horizon : int
            Forecast horizon in days.

        Returns
        -------
        float
            Annualised volatility.
        """
        daily_vol = self.forecast_volatility(horizon)
        return daily_vol * np.sqrt(252)

    # ------------------------------------------------------------------ #
    #  Rolling volatility                                                 #
    # ------------------------------------------------------------------ #
    def get_rolling_volatility(self, step: int = 1) -> pd.Series:
        """
        Compute rolling conditional volatility via expanding/sliding EGARCH fits.

        For production use with large datasets, this performs a rolling fit
        every ``step`` days and forward-fills between steps for efficiency.

        Parameters
        ----------
        step : int
            Re-fit every ``step`` days (default 1).  Higher values trade
            accuracy for speed (e.g. step=5 → ~5× faster).

        Returns
        -------
        pd.Series
            Daily conditional volatility (decimal, not percentage).
        """
        n = len(self.returns)
        start = min(self.window, n)

        rolling_vols: list[float] = []
        dates: list = []
        last_vol: float = np.nan

        logger.info(
            f"[GARCHEstimator] Computing rolling volatility "
            f"(window={self.window}, step={step}, obs={n - start})"
        )

        for i in range(start, n):
            if (i - start) % step == 0:
                window_returns = self.returns.iloc[max(0, i - self.window): i]

                try:
                    temp_model = arch_model(
                        window_returns * 100,
                        vol="EGARCH",
                        p=1,
                        q=1,
                        dist="normal",
                    )
                    temp_results = temp_model.fit(disp="off", show_warning=False)

                    forecast_var = temp_results.forecast(horizon=1).variance.values[-1, 0]
                    last_vol = float(np.sqrt(forecast_var) / 100.0)
                    last_vol = float(np.clip(last_vol, 0.001, 10.0))

                except Exception:
                    # Keep previous volatility on numerical failure
                    pass

            rolling_vols.append(last_vol)
            dates.append(self.returns.index[i])

        series = pd.Series(rolling_vols, index=dates, name="garch_volatility")

        # Interpolate any remaining NaN values
        series = series.interpolate(method="linear").bfill().ffill()

        logger.info(
            f"[GARCHEstimator] Rolling volatility complete — "
            f"{len(series)} observations, "
            f"mean={series.mean():.4f}, max={series.max():.4f}"
        )

        return series

    # ------------------------------------------------------------------ #
    #  Conditional variance extraction                                    #
    # ------------------------------------------------------------------ #
    def get_conditional_variance(self) -> pd.Series:
        """
        Extract conditional volatility from fitted model (in-sample).

        Returns
        -------
        pd.Series
            In-sample conditional volatility (decimal, not percentage).

        Raises
        ------
        ValueError
            If the model has not been fitted.
        """
        if self.fitted_results is None:
            raise ValueError("Model must be fitted first.  Call fit().")

        return self.fitted_results.conditional_volatility / 100.0

    # ------------------------------------------------------------------ #
    #  Persistence & Serialisation                                        #
    # ------------------------------------------------------------------ #
    def save(self, path: str) -> None:
        """Save fitted model to disk via joblib."""
        import joblib

        if self.fitted_results is None:
            raise ValueError("Cannot save unfitted model.")

        joblib.dump(
            {
                "fitted_results": self.fitted_results,
                "window": self.window,
                "returns_tail": self.returns.tail(self.window),
            },
            path,
        )
        logger.info(f"[GARCHEstimator] Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> "GARCHVolatilityEstimator":
        """Load a previously saved model."""
        import joblib

        data = joblib.load(path)
        instance = cls(data["returns_tail"], window=data["window"])
        instance.fitted_results = data["fitted_results"]
        return instance

    def __repr__(self) -> str:
        status = "fitted" if self.fitted_results else "unfitted"
        return (
            f"<GARCHVolatilityEstimator [{status}] "
            f"window={self.window}, obs={len(self.returns)}>"
        )
