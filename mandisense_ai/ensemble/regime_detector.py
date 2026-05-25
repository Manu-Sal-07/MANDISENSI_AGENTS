"""
Regime Detector.

Simple detection logic for evaluating the current market state.
Identifies High Volatility, Festival periods, and Supply Shocks.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)


class RegimeDetector:
    """Detects distinct market regimes to trigger ensemble weight boosts."""

    def __init__(self, volatility_threshold: float = 0.05, shock_threshold: float = 0.4):
        self.volatility_threshold = volatility_threshold
        self.shock_threshold = shock_threshold

    def detect_regime(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Evaluate the latest window of data for active regimes.

        Args:
            df: DataFrame containing at least 'modal_price', 'arrivals_tonnes',
                and 'is_festival' if available.

        Returns:
            Dictionary with boolean flags for each regime.
        """
        if df.empty or len(df) < 7:
            return {"high_volatility": False, "festival": False, "supply_shock": False}

        latest = df.iloc[-1]
        recent_window = df.tail(14)

        # 1. Festival Period
        is_festival = False
        if "is_festival" in df.columns:
            # Check if there is a festival within the last 3 days or next 7 days
            # using 'is_festival' flag. Since we only have historical data here,
            # we just check recent window.
            is_festival = bool(recent_window["is_festival"].sum() > 0)

        # 2. High Volatility
        high_volatility = False
        if "modal_price" in df.columns:
            # Calculate daily percentage returns
            returns = recent_window["modal_price"].pct_change().dropna()
            if not returns.empty:
                std_dev = returns.std()
                if std_dev > self.volatility_threshold:
                    high_volatility = True

        # 3. Supply Shock
        supply_shock = False
        if "arrivals_tonnes" in df.columns:
            # Calculate 30-day moving average and compare latest
            long_window = df.tail(30)
            mean_arrival = long_window["arrivals_tonnes"].mean()
            if mean_arrival > 0:
                deviation = abs(latest["arrivals_tonnes"] - mean_arrival) / mean_arrival
                if deviation > self.shock_threshold:
                    supply_shock = True
        
        # Or if arrival_deviation_pct already computed in feature engineering
        if "arrival_deviation_pct" in latest:
            if abs(latest["arrival_deviation_pct"]) > self.shock_threshold:
                supply_shock = True

        regimes = {
            "high_volatility": high_volatility,
            "festival": is_festival,
            "supply_shock": supply_shock,
        }
        
        logger.debug(f"[RegimeDetector] Detected regimes: {regimes}")
        return regimes
