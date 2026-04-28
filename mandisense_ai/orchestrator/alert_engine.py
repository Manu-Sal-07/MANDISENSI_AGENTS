import logging
from typing import List, Dict, Optional
from api.schemas.models import AlertItem, PredictResponse

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Evaluates market conditions against user-defined alerts.
    In a full production system, this runs as a background worker (Celery/RQ)
    or is triggered post-prediction to check all active alerts.
    """
    
    def __init__(self):
        # In-memory mock DB for alerts. Replace with real DB connection.
        self.active_alerts: List[AlertItem] = []
        
    def register_alert(self, alert: AlertItem) -> AlertItem:
        self.active_alerts.append(alert)
        logger.info(f"Registered new alert for {alert.commodity} @ {alert.mandi}: {alert.alert_type}")
        return alert

    def evaluate_predictions(self, prediction_result: PredictResponse) -> List[AlertItem]:
        """
        Check if the newly generated prediction triggers any active alerts
        for the given commodity and mandi.
        """
        triggered_alerts = []
        
        for alert in self.active_alerts:
            if alert.status != "ACTIVE":
                continue
                
            if alert.commodity != prediction_result.commodity or alert.mandi != prediction_result.mandi:
                continue

            is_triggered = False
            pred = prediction_result.prediction
            guidance = prediction_result.farmer_guidance

            if alert.alert_type == "PRICE_DROP" and guidance.decision == "SELL":
                # Price is expected to drop, triggering a SELL decision
                is_triggered = True
                
            elif alert.alert_type == "PRICE_RISE" and guidance.decision == "WAIT":
                # Price is expected to rise, triggering a WAIT decision
                is_triggered = True
                
            elif alert.alert_type == "TREND_CHANGE" and prediction_result.risk_flags.high_volatility_risk:
                # Volatility detected
                is_triggered = True

            if is_triggered:
                alert.status = "TRIGGERED"
                triggered_alerts.append(alert)
                logger.warning(f"ALERT TRIGGERED! {alert.alert_type} for {alert.commodity}")

        return triggered_alerts

# Singleton instance for simple integration
alert_engine = AlertEngine()
