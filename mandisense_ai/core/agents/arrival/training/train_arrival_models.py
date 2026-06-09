import pandas as pd
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import joblib

from mandisense_ai.config.settings import settings

from mandisense_ai.core.agents.arrival.models import ARRIVAL_MODEL_REGISTRY
from mandisense_ai.ensemble.agent_ensemble import AgentEnsemble
from mandisense_ai.ensemble.feedback_store import FeedbackStore
from mandisense_ai.ensemble.regime_detector import RegimeDetector
from mandisense_ai.ensemble.dynamic_weighter import DynamicWeighter
from mandisense_ai.utils.logger import get_logger
from mandisense_ai.core.agents.arrival_volume_agent import build_arrival_features

logger = get_logger(__name__)

def save_arrival_bundle(bundle: dict, commodity: str, mandi: str) -> None:
    """
    Serializes all trained models and ensemble artifacts to disk.
    Ensures directory exists and file is written safely using joblib.
    """
    safe_commodity = str(commodity).strip().lower().replace(" ", "_").replace("/", "-")
    safe_mandi = str(mandi).strip().lower().replace(" ", "_").replace("/", "-")
    
    base_dir = Path(settings.paths.models_dir) if hasattr(settings.paths, 'models_dir') else Path("models")
    if base_dir.name != "arrival":
        base_dir = base_dir / "arrival"
    # Transitioning to commodity-level bundles
    save_dir = base_dir / safe_commodity
    
    try:
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / "bundle.pkl"
        joblib.dump(bundle, save_path)
        
        n_models = len(bundle.get("models", {}))
        feature_count = len(bundle.get("feature_columns", []))
        timestamp = bundle.get("metadata", {}).get("trained_at", "unknown")
        
        logger.info(f"Successfully saved arrival bundle to {save_path}")
        logger.info(f"Bundle summary | Models: {n_models} | Features: {feature_count} | Timestamp: {timestamp}")
    except Exception as e:
        logger.error(f"Failed to save arrival bundle for {commodity}_{mandi}: {str(e)}")
        raise


def train_arrival_models(data: pd.DataFrame, commodity: str = "Unknown", mandi: str = "Unknown") -> dict:
    """
    Trains the arrival models and computes their weights.
    Responsible ONLY for training, CV, and weight computation.
    """
    df_fe = build_arrival_features(data)

    # Target: 7-day forward price change %
    df_fe['future_price_7d'] = df_fe['modal_price'].shift(-7)
    df_fe['target_7d_pct']   = (
        (df_fe['future_price_7d'] - df_fe['modal_price'])
        / (df_fe['modal_price'] + 1e-9) * 100.0
    )
    
    # Winsorize target to realistic range: clip to ±25% per 7 days
    # Prevents extreme price events from dominating CV and producing wild predictions
    _TARGET_CLIP = 25.0
    df_fe['target_7d_pct'] = df_fe['target_7d_pct'].clip(lower=-_TARGET_CLIP, upper=_TARGET_CLIP)

    # Drop rows without a valid target
    df_model = df_fe.dropna(subset=['target_7d_pct']).copy()

    # ── Feature columns (same set for ALL models) ──────────────────
    feature_cols = [
        'mandi_id',
        'arrivals_7d_mean', 'arrivals_30d_mean', 'arrival_deviation_pct',
        'arrival_yoy_deviation_pct', 'consecutive_decline_days',
        'supply_momentum_slope',
        'arrivals_lag_1', 'arrivals_lag_7', 'price_lag_1', 'price_lag_7',
        'rolling_elasticity_30d', 'is_festival',
    ]

    # Ensure we only use columns that exist
    X_cols = [c for c in feature_cols if c in df_model.columns]

    ensemble = AgentEnsemble(
        models=ARRIVAL_MODEL_REGISTRY,
        n_splits=5,
        top_n=8
    )

    regime_flags = df_model['is_festival'] if 'is_festival' in df_model.columns else None

    ensemble.fit(
        df_model[X_cols],
        df_model['target_7d_pct'],
        regime_flags=regime_flags
    )

    detector = RegimeDetector()
    regimes = detector.detect_regime(df_model)

    feedback_store = FeedbackStore()
    weighter = DynamicWeighter(feedback_store)

    adjusted_weights = weighter.adjust_weights(
        base_weights=ensemble.weights,
        agent_type='ArrivalVolume',
        commodity=commodity,
        mandi=mandi,
        regimes=regimes
    )
    ensemble.weights = adjusted_weights

    # Format the required output dictionary
    model_names = list(ensemble._fitted_models.keys())
    
    bundle = {
        "models": ensemble._fitted_models,
        "weights": ensemble.weights,
        "feature_columns": X_cols,
        "metadata": {
            "cv_scores": ensemble.errors,
            "n_samples": len(df_model),
            "trained_at": datetime.utcnow().isoformat(),
            "model_names": model_names,
            "ensemble_log": ensemble.get_ensemble_log(),
            "best_model_name": ensemble.best_model_name,
            "n_active_models": ensemble.n_active_models
        }
    }
    
    save_arrival_bundle(bundle, commodity, mandi)
    
    return bundle
