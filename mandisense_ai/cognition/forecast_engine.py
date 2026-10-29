"""
The cognition council's price signal, taken from the validated forecast service.

The council used to call `DecisionGradeInferenceEngine`, which loaded per-commodity "v3" models and a "v4" dataset that no
longer exist (the v4 data was a synthetic seasonal backfill and was removed). Every state therefore came back as
"No models found", with a zero price and a safety freeze. This engine answers the same call, `predict(commodity, mandi)`,
from the walk-forward-validated multi-horizon forecasts instead, so the council reasons over real numbers:

* price and direction: the forecast at the council's horizon (5 days, else the nearest promoted one);
* confidence: the model's own probability for the direction it calls, never above what it has earned on held-out folds;
* arrivals: the recent observed level against its trailing norm. There is no arrivals forecast, so none is claimed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from mandisense_ai.forecasting.naming import forecast_market

logger = logging.getLogger("ForecastBackedEngine")

COUNCIL_HORIZON = 5
IMPLAUSIBLE_MOVE_PCT = 40.0


class ForecastBackedEngine:
    def __init__(self) -> None:
        self._service = None

    @property
    def service(self):
        if self._service is None:
            from mandisense_ai.forecasting.service import get_forecast_service

            self._service = get_forecast_service()
        return self._service

    def _curve(self, commodity: str, mandi_id: str) -> List[Dict[str, Any]]:
        if not self.service.is_available:
            return []
        rows = self.service.get_curve(commodity, forecast_market(mandi_id)) or []
        return [r for r in rows if r.get("status") == "OK"]

    def has_series(self, commodity: str, mandi_id: str) -> bool:
        return bool(self._curve(commodity, mandi_id))

    def pick(self, commodity: str, mandi_id: str) -> Optional[Dict[str, Any]]:
        rows = self._curve(commodity, mandi_id)
        if not rows:
            return None
        return min(rows, key=lambda r: abs(int(r["horizon_days"]) - COUNCIL_HORIZON))

    def last_price(self, commodity: str, mandi_id: str) -> Optional[float]:
        row = self.pick(commodity, mandi_id)
        return float(row["last_observed_price"]) if row and row.get("last_observed_price") else None

    def decision(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        row = self.pick(commodity, mandi_id)
        if row is None:
            return {"decision": "WAIT", "reasoning": "No validated forecast for this series."}
        p = row.get("decision_probability_of_decline")
        words = f"{row['horizon_days']}-day forecast {row['expected_change_pct']:+.1f}%"
        if p is not None:
            words += f", {p * 100:.0f}% chance the price is lower"
        return {"decision": row.get("decision", "WAIT"), "reasoning": words + f"; model skill vs no-change {row.get('model_skill', 0) * 100:+.1f}%."}

    def _arrivals(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        try:
            from mandisense_ai.services import candle_data_service as cds

            s = cds.get_daily_series(commodity, mandi_id)["arrivals"].dropna()
            if len(s) >= 10:
                recent, norm = float(s.tail(7).mean()), float(s.tail(60).mean())
                ratio = recent / norm if norm > 0 else 1.0
                return {"level": recent, "signal": "high" if ratio > 1.3 else "low" if ratio < 0.7 else "normal", "ratio": ratio}
        except Exception as exc:  # arrivals are context, never a reason to fail the forecast
            logger.debug("arrivals unavailable for %s/%s: %s", commodity, mandi_id, exc)
        return {"level": 0.0, "signal": "unknown", "ratio": None}

    async def predict(self, commodity: str, mandi_id: str) -> Dict[str, Any]:
        row = self.pick(commodity, mandi_id)
        if row is None:
            raise ValueError(f"No validated forecast for {commodity} @ {mandi_id}")
        change = float(row["expected_change_pct"])
        trend = "up" if change > 1.0 else "down" if change < -1.0 else "stable"
        p_decline = row.get("decision_probability_of_decline")
        p_called = max(p_decline, 1 - p_decline) if p_decline is not None else 0.5
        if abs(change) > IMPLAUSIBLE_MOVE_PCT:
            # A move this large in a few days is outside what the model was validated on (usually a reporting quirk in the latest
            # price, e.g. a different grade quoted that day). Say so and give it almost no weight rather than present it as a call.
            p_called = min(p_called, 0.2)
        arr = self._arrivals(commodity, mandi_id)
        iv = row.get("interval") or {}
        evidence = (f"{row['horizon_days']}-day forecast {row['forecast_price']:.0f} against {row['last_observed_price']:.0f} now "
                    f"({change:+.1f}%); 90% band {iv.get('p05', 0):.0f}-{iv.get('p95', 0):.0f}; "
                    f"skill over no-change {row.get('model_skill', 0) * 100:+.1f}% on held-out folds.")
        if abs(change) > IMPLAUSIBLE_MOVE_PCT:
            evidence += " This move is larger than the model was validated on, so it is given very little weight."
        return {"predicted_price": float(row["forecast_price"]), "confidence": float(p_called), "trend": trend, "explanation": evidence,
                "predicted_arrivals": arr["level"], "arrival_signal": arr["signal"], "horizon_days": int(row["horizon_days"]),
                "source": row.get("prediction_source", "forecast_service")}
