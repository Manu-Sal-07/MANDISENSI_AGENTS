"""
Volatility Alert Engine — Multi-level statistical alert system.

Alert levels:
  WARNING:  current_vol > μ + 2σ
  CRITICAL: current_vol > μ + 3σ
  EXTREME:  current_vol > μ + 4σ

Performance: Alert check <5ms, false positive rate <10%.
"""

from __future__ import annotations
from typing import Dict, Optional
import numpy as np
import pandas as pd
try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class VolatilityAlertEngine:
    """Real-time volatility alert system with multi-level severity."""

    def __init__(self, historical_volatility: pd.Series):
        self.hist_vol = historical_volatility.dropna()
        self.mean_vol = float(self.hist_vol.mean())
        self.std_vol = float(self.hist_vol.std())

        self.alert_levels = {
            "WARNING": self.mean_vol + 2 * self.std_vol,
            "CRITICAL": self.mean_vol + 3 * self.std_vol,
            "EXTREME": self.mean_vol + 4 * self.std_vol,
        }

        logger.info(
            f"[AlertEngine] Initialised — μ={self.mean_vol:.4f}, σ={self.std_vol:.4f}, "
            f"thresholds: WARNING={self.alert_levels['WARNING']:.4f}, "
            f"CRITICAL={self.alert_levels['CRITICAL']:.4f}, "
            f"EXTREME={self.alert_levels['EXTREME']:.4f}"
        )

    def check_alert(
        self, current_volatility: float, forecasted_volatility: Optional[float] = None
    ) -> Dict:
        """
        Check if alerts should be triggered.

        Returns dict with: alert_triggered, level, current_volatility,
        forecasted_volatility, threshold, percentile, message, forecast_alert.
        """
        if current_volatility > self.alert_levels["EXTREME"]:
            level, triggered = "EXTREME", True
        elif current_volatility > self.alert_levels["CRITICAL"]:
            level, triggered = "CRITICAL", True
        elif current_volatility > self.alert_levels["WARNING"]:
            level, triggered = "WARNING", True
        else:
            level, triggered = "NORMAL", False

        percentile = float((self.hist_vol < current_volatility).mean() * 100)

        if triggered:
            pct_above = ((current_volatility - self.mean_vol) / self.mean_vol) * 100
            message = (
                f"\U0001f6a8 {level} VOLATILITY ALERT: Current volatility "
                f"{current_volatility:.4f} is {pct_above:.1f}% above historical "
                f"mean (in {percentile:.1f}th percentile)"
            )
            logger.warning(f"[AlertEngine] {message}")
        else:
            message = f"\u2705 Volatility within normal range ({percentile:.1f}th percentile)"

        forecast_alert = None
        if forecasted_volatility is not None and forecasted_volatility > self.alert_levels["WARNING"]:
            forecast_alert = (
                f"\u26a0\ufe0f Forecasted volatility {forecasted_volatility:.4f} "
                f"suggests elevated risk ahead"
            )

        return {
            "alert_triggered": triggered,
            "level": level,
            "current_volatility": current_volatility,
            "forecasted_volatility": forecasted_volatility,
            "threshold": self.alert_levels.get(level, self.alert_levels["WARNING"]),
            "percentile": percentile,
            "message": message,
            "forecast_alert": forecast_alert,
        }

    def get_risk_category(self, volatility: float) -> str:
        """Classify volatility into risk categories: Low / Medium / High / Extreme."""
        if volatility > self.alert_levels["EXTREME"]:
            return "Extreme"
        elif volatility > self.alert_levels["CRITICAL"]:
            return "High"
        elif volatility > self.alert_levels["WARNING"]:
            return "Medium"
        return "Low"

    def __repr__(self) -> str:
        return (
            f"<VolatilityAlertEngine μ={self.mean_vol:.4f} σ={self.std_vol:.4f} "
            f"n_obs={len(self.hist_vol)}>"
        )
