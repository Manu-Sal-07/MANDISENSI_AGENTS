"""Arrival Volume Agent

Refactored Phase 1: Decoupled Training Logic from Inference Logic.
"""

import copy
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
import joblib
from pathlib import Path

from sklearn.linear_model import LinearRegression
import scipy.stats as stats

from mandisense_ai.config.settings import settings, AgentOutput
from mandisense_ai.data.repository import DataRepository
from mandisense_ai.utils.logger import get_logger
from mandisense_ai.core.agents.seasonality_agent import merge_festivals

logger = get_logger(__name__)

MANDI_MAP = {
    "kolar": 0,
    "lasalgaon": 1,
    "agra": 2,
    "guntur": 3,
    "neemuch": 4,
    "bangalore": 5,
    "unknown": 99
}

from functools import lru_cache

@lru_cache(maxsize=10)
def load_arrival_bundle(commodity: str, mandi: str) -> dict:
    """
    Loads and validates the pretrained arrival model bundle from disk.
    Ensures zero training logic executes at runtime.
    """
    safe_commodity = str(commodity).strip().lower().replace(" ", "_").replace("/", "-")
    safe_mandi = str(mandi).strip().lower().replace(" ", "_").replace("/", "-")
    
    base_dir = Path(settings.paths.models_dir) if hasattr(settings.paths, 'models_dir') else Path("models")
    if base_dir.name != "arrival":
        base_dir = base_dir / "arrival"
    # Transitioning to commodity-level bundles
    bundle_path = base_dir / safe_commodity / "bundle.pkl"
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Arrival bundle not found at {bundle_path}")
        
    try:
        bundle = joblib.load(bundle_path)
    except Exception as e:
        raise ValueError(f"Failed to load arrival bundle: {str(e)}")
        
    # Validation checks
    models = bundle.get("models", {})
    if not models:
        raise ValueError("Validation failed: Models missing or empty in bundle")
        
    weights = bundle.get("weights", {})
    if not weights:
        raise ValueError("Validation failed: Weights missing or empty in bundle")
        
    if set(models.keys()) != set(weights.keys()):
        raise ValueError("Validation failed: Models and weights keys do not match")
        
    feature_columns = bundle.get("feature_columns")
    if not feature_columns or not isinstance(feature_columns, list):
        raise ValueError("Validation failed: feature_columns missing or invalid in bundle")
        
    n_models = len(models)
    timestamp = bundle.get("metadata", {}).get("trained_at", "unknown")
    logger.info(f"Loaded arrival bundle from {bundle_path} successfully. Models: {n_models}, Timestamp: {timestamp}")
    
    return bundle


def build_arrival_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Responsible ONLY for computing supply features, momentum features, and lag features.
    """
    d = df.copy()
    d['date'] = pd.to_datetime(d['date'])
    d = d.sort_values(['mandi', 'date']).reset_index(drop=True)
    
    # Extract mandi_id if mandi column exists
    if 'mandi' in d.columns:
        d['mandi_id'] = d['mandi'].map(lambda x: MANDI_MAP.get(str(x).lower(), MANDI_MAP['unknown']))
    elif 'mandi_id' not in d.columns:
        d['mandi_id'] = MANDI_MAP['unknown']

    # Rolling arrival features
    d['arrivals_7d_mean']  = d['arrivals_tonnes'].rolling(7,  min_periods=1).mean()
    d['arrivals_30d_mean'] = d['arrivals_tonnes'].rolling(30, min_periods=1).mean()
    d['arrival_deviation_pct'] = (
        (d['arrivals_tonnes'] - d['arrivals_30d_mean'])
        / (d['arrivals_30d_mean'] + 1e-9)
    )

    # YoY comparison
    d['arrivals_yoy'] = d['arrivals_tonnes'].shift(365)
    d['arrival_yoy_deviation_pct'] = (
        (d['arrivals_tonnes'] - d['arrivals_yoy']) / (d['arrivals_yoy'] + 1e-9)
    )

    # Consecutive decline days
    d['arrivals_diff'] = d['arrivals_tonnes'].diff()
    d['consecutive_decline_days'] = (d['arrivals_diff'] < 0).astype(int)
    d['consecutive_decline_days'] = (
        d['consecutive_decline_days']
        * d['consecutive_decline_days'].groupby(
            (d['consecutive_decline_days'] == 0).cumsum()
        ).cumsum()
    )

    # 14-day momentum slope
    d['supply_momentum_slope'] = d['arrivals_tonnes'].rolling(14).apply(
        lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) >= 2 else 0.0,
        raw=False,
    )

    # Lag features
    for lag in [1, 7, 14, 30]:
        d[f'arrivals_lag_{lag}'] = d['arrivals_tonnes'].shift(lag)
        d[f'price_lag_{lag}']    = d['modal_price'].shift(lag)

    # Rolling log-log elasticity (30-day window)
    elasticities = []
    for i in range(len(d)):
        start  = max(0, i - 30 + 1)
        window = d.iloc[start : i + 1]
        if len(window) < 10:
            elasticities.append(0.0)
            continue
        with np.errstate(divide='ignore', invalid='ignore'):
            lp = np.log(window['modal_price'].replace(0, np.nan)).dropna()
            la = np.log(window['arrivals_tonnes'].replace(0, np.nan)).dropna()
        if len(lp) < 10 or len(la) < 10:
            elasticities.append(0.0)
            continue
        try:
            lr  = LinearRegression()
            idx = lp.index.intersection(la.index)
            lr.fit(la.loc[idx].values.reshape(-1, 1), lp.loc[idx].values)
            elasticities.append(float(lr.coef_[0]))
        except Exception:
            elasticities.append(0.0)
    d['rolling_elasticity_30d'] = elasticities

    return d

def build_arrival_inference_features(data: pd.DataFrame, timestamp: datetime, feature_columns: list, mandi: str) -> pd.DataFrame:
    """
    Real-Time Feature Engineering for Supply Dynamics.
    Constructs a deterministic feature vector using strict historical data cutoff.
    """
    ts = pd.to_datetime(timestamp)
    
    # 2. Strict Data Cutoff
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] <= ts].sort_values(['mandi', 'date']).reset_index(drop=True)
    
    if df.empty:
        raise ValueError(f"No historical data available prior to timestamp {ts}")
        
    # 3. Define Rolling Window (e.g. 400 days to comfortably calculate 365-day YoY and 30-day means)
    window_data = df.tail(400).copy().reset_index(drop=True)
    
    # 4. Compute Supply Features
    arrivals = window_data['arrivals_tonnes'].ffill().fillna(0)
    
    arrival_7d_mean = arrivals.tail(7).mean() if len(arrivals) >= 7 else arrivals.mean()
    arrival_30d_mean = arrivals.tail(30).mean() if len(arrivals) >= 30 else arrivals.mean()
    
    current_tonnes = arrivals.iloc[-1]
    arrival_deviation_pct = (current_tonnes - arrival_30d_mean) / (arrival_30d_mean + 1e-9)
    if len(window_data) >= 365:
        yoy_tonnes = window_data.iloc[-365]['arrivals_tonnes']
        arrival_yoy_deviation_pct = (current_tonnes - yoy_tonnes) / (yoy_tonnes + 1e-9)
    else:
        arrival_yoy_deviation_pct = 0.0
        
    # 5. Compute Momentum Features
    last_14 = arrivals.tail(14).values
    arrival_slope = float(np.polyfit(np.arange(len(last_14)), last_14, 1)[0]) if len(last_14) >= 2 else 0.0
    
    diffs = arrivals.diff().tail(30).values
    consecutive_decline_days = 0
    for d in reversed(diffs):
        if np.isnan(d): break
        if d < 0: consecutive_decline_days += 1
        else: break
        
    # 6. Price Interaction Features
    prices = window_data['modal_price'].ffill().fillna(0)
    price_lag_1 = prices.iloc[-2] if len(prices) >= 2 else prices.iloc[-1]
    price_lag_7 = prices.iloc[-8] if len(prices) >= 8 else prices.iloc[-1]
    
    arrivals_lag_1 = arrivals.iloc[-2] if len(arrivals) >= 2 else current_tonnes
    arrivals_lag_7 = arrivals.iloc[-8] if len(arrivals) >= 8 else current_tonnes
    
    last_30_df = window_data.tail(30)
    with np.errstate(divide='ignore', invalid='ignore'):
        lp = np.log(last_30_df['modal_price'].replace(0, np.nan)).dropna()
        la = np.log(last_30_df['arrivals_tonnes'].replace(0, np.nan)).dropna()
        
    elasticity = 0.0
    if len(lp) >= 10 and len(la) >= 10:
        try:
            lr = LinearRegression()
            idx = lp.index.intersection(la.index)
            if len(idx) >= 10:
                lr.fit(la.loc[idx].values.reshape(-1, 1), lp.loc[idx].values)
                elasticity = float(lr.coef_[0])
        except Exception:
            pass
            
    is_festival = window_data.iloc[-1].get('is_festival', 0)
    
    # 7. Supply Regime Features
    dev_score = np.tanh(np.abs(arrival_deviation_pct))
    yoy_score = np.tanh(np.abs(arrival_yoy_deviation_pct))
    momentum_score = np.tanh(np.abs(arrival_slope) / (arrival_30d_mean + 1e-9))
    
    supply_stress_score = float(np.clip(
        dev_score * 0.45 + yoy_score * 0.35 + momentum_score * 0.2, 0.0, 1.0
    ))
    
    if supply_stress_score > 0.8: supply_regime = 'squeeze'
    elif supply_stress_score > 0.6: supply_regime = 'tightening'
    elif supply_stress_score < 0.2: supply_regime = 'oversupply'
    else: supply_regime = 'normal'
    
    # 8. Construct Feature Dictionary
    features_dict = {
        'arrivals_7d_mean': arrival_7d_mean,
        'arrivals_30d_mean': arrival_30d_mean,
        'arrival_deviation_pct': arrival_deviation_pct,
        'arrival_yoy_deviation_pct': arrival_yoy_deviation_pct,
        'consecutive_decline_days': consecutive_decline_days,
        'supply_momentum_slope': arrival_slope,
        'arrivals_lag_1': arrivals_lag_1,
        'arrivals_lag_7': arrivals_lag_7,
        'price_lag_1': price_lag_1,
        'price_lag_7': price_lag_7,
        'rolling_elasticity_30d': elasticity,
        'is_festival': is_festival,
        'mandi_id': float(MANDI_MAP.get(mandi.lower(), MANDI_MAP['unknown'])),
        
        # Meta values for agent output processing
        'supply_stress_score': supply_stress_score,
        'supply_regime': supply_regime,
        'modal_price': prices.iloc[-1],
        'arrivals_tonnes': current_tonnes
    }
    
    # 9. Feature Alignment (CRITICAL)
    features = pd.DataFrame([features_dict])
    aligned_features = features.reindex(columns=feature_columns, fill_value=0)
    
    # 10. Validation Guard
    assert not aligned_features.isnull().values.any(), "Features contain NaN values"
    assert not np.isinf(aligned_features.values).any(), "Features contain inf values"
    assert aligned_features.shape == (1, len(feature_columns)), f"Shape mismatch: {aligned_features.shape} != (1, {len(feature_columns)})"
    assert list(aligned_features.columns) == feature_columns, "Column mismatch"
    
    logger.info(f"Generated real-time features for timestamp {ts}. Window size: {len(window_data)}.")
    
    # Attach meta without breaking DataFrame structure
    aligned_features.attrs['meta'] = features_dict
    
    return aligned_features

def compute_confidence(
    model_predictions: Dict[str, float], 
    cv_scores: Dict[str, float], 
    supply_stress: float, 
    final_pred: float
) -> float:
    """Computes a multi-factor confidence score for the prediction."""
    preds = list(model_predictions.values())
    
    # (A) Model Agreement
    if len(preds) > 1:
        std_pred = float(np.std(preds))
        agreement_score = float(np.clip(1.0 - (std_pred / 10.0), 0.0, 1.0))
    else:
        agreement_score = 0.5
        
    # (B) Training Performance
    valid_mapes = [cv_scores.get(m, 1.0) for m in model_predictions.keys()]
    avg_mape = float(np.mean(valid_mapes)) if valid_mapes else 1.0
    inverse_mape_score = float(np.clip(1.0 - avg_mape, 0.0, 1.0))
    
    # (C) Signal Strength
    signal_strength_score = float(np.clip(abs(final_pred) / 10.0, 0.0, 1.0))
    
    # (D) Supply Volatility Penalty
    penalty = supply_stress * 0.4
    
    raw_confidence = (agreement_score * 0.4) + (inverse_mape_score * 0.4) + (signal_strength_score * 0.2)
    confidence = raw_confidence - penalty
    
    return float(np.clip(confidence, 0.05, 0.95))

def predict_with_ensemble(bundle: dict, features: pd.DataFrame) -> dict:
    """
    Responsible ONLY for per-model prediction and weighted aggregation.
    """
    feature_cols = bundle['feature_columns']
    models = bundle['models']
    weights = bundle['weights']

    last_row = features.iloc[-1:].copy()
    
    # Feature Alignment Preparation
    for col in feature_cols:
        if col not in last_row.columns:
            logger.warning(f"Missing feature '{col}' during inference. Padding with 0.0.")
            last_row[col] = 0.0
            
    X_last = last_row[feature_cols].fillna(0)

    # 1 & 2. Per-Model Prediction & Validation
    valid_predictions = {}
    valid_weights = {}

    for name, model in models.items():
        try:
            pred = float(model.predict(X_last)[0])
            if np.isnan(pred) or np.isinf(pred):
                logger.warning(f"Model {name} produced non-finite prediction: {pred}. Excluding.")
                continue
            valid_predictions[name] = pred
            valid_weights[name] = weights.get(name, 0.0)
        except Exception as e:
            logger.warning(f"Model {name} prediction failed: {str(e)}. Excluding.")

    if not valid_predictions:
        raise ValueError("ALL models failed to predict. Cannot compute ensemble.")

    # 3. Weighted Ensemble Aggregation
    total_weight = sum(valid_weights.values())
    if total_weight <= 0:
        logger.warning("Total valid weight is zero, using uniform weights.")
        valid_weights = {k: 1.0 / len(valid_weights) for k in valid_weights}
        total_weight = 1.0
        
    final_prediction = 0.0
    normalized_weights = {}
    for name, pred in valid_predictions.items():
        w = valid_weights[name] / total_weight
        normalized_weights[name] = w
        final_prediction += w * pred

    # 4. (Removed excessive clamping per Fix 6)
    # final_prediction = float(np.clip(final_prediction, -15.0, 15.0))
    
    # 5. Compute Confidence
    supply_stress = features.attrs.get('meta', {}).get('supply_stress_score', 0.0)
    cv_scores = bundle.get("metadata", {}).get("cv_scores", {})
    confidence = compute_confidence(valid_predictions, cv_scores, supply_stress, final_prediction)

    return {
        "prediction": final_prediction,
        "confidence": confidence,
        "model_predictions": valid_predictions,
        "normalized_weights": normalized_weights,
        "prediction_std": float(np.std(list(valid_predictions.values()))) if len(valid_predictions) > 1 else 0.0
    }

def _compute_festival_arrival_metrics(df: pd.DataFrame) -> float:
    if 'is_festival' in df.columns and df['is_festival'].sum() > 0:
        fest_mean = df.loc[df['is_festival'] == 1, 'arrivals_tonnes'].mean()
        base_mean = df.loc[df['is_festival'] == 0, 'arrivals_tonnes'].mean()
        if pd.notna(fest_mean) and pd.notna(base_mean) and base_mean != 0:
            return float((fest_mean - base_mean) / (base_mean + 1e-9) * 100.0)
    return 0.0

def _supply_regime(score: float) -> str:
    if score > 0.8:   return 'Squeeze'
    if score > 0.6:   return 'Tightening'
    if score < 0.2:   return 'Oversupply'
    return 'Normal'

def run_arrival_volume_agent(
    commodity: str, mandi: str, target_date: Optional[date] = None
) -> AgentOutput:
    repo = DataRepository()
    
    # 1. Load Data
    data = repo.get_processed_data(commodity, mandi)
    
    if data.empty:
        logger.error('No processed data')
        return AgentOutput(
            agent_name="ArrivalVolume",
            prediction=0.0,
            confidence=0.0,
            metadata={
                "commodity": commodity,
                "mandi": mandi,
                "timestamp": str(datetime.utcnow()),
                "error": "No processed data available"
            }
        )

    data = data.sort_values('date').reset_index(drop=True)
    data = merge_festivals(data)

    # 2. Load Pretrained Bundle (Pure Inference System)
    try:
        bundle = load_arrival_bundle(commodity, mandi)
    except Exception as e:
        logger.warning(f"Failed to load bundle for {commodity}_{mandi}: {str(e)}. Triggering Option A fallback.")
        from mandisense_ai.core.agents.arrival.training.train_arrival_models import train_arrival_models
        train_arrival_models(data, commodity=commodity, mandi=mandi)
        bundle = load_arrival_bundle(commodity, mandi)

    timestamp = pd.to_datetime(target_date) if target_date else pd.to_datetime(data['date'].max())

    # 3. Build Real-Time Inference Features
    features_df = build_arrival_inference_features(data, timestamp, bundle['feature_columns'], mandi)
    meta = features_df.attrs.get('meta', {})

    # 4. Predict
    prediction_result = predict_with_ensemble(bundle, features_df)
    pred = prediction_result["prediction"]
    
    # ── Return std & P_positive ──
    latest = pd.to_datetime(data['date'].max())
    mask   = []
    for y_ in range(1, 6):
        try:
            dt_prev = latest - pd.DateOffset(years=y_)
        except Exception:
            dt_prev = latest - pd.Timedelta(days=365 * y_)
        low_  = dt_prev - pd.Timedelta(days=15)
        high_ = dt_prev + pd.Timedelta(days=15)
        mask.append(
            (pd.to_datetime(data['date']) >= low_)
            & (pd.to_datetime(data['date']) <= high_)
        )

    if mask:
        mask_all = mask[0]
        for m in mask[1:]:
            mask_all = mask_all | m
        window_df = data[mask_all]
    else:
        window_df = data

    with np.errstate(divide='ignore', invalid='ignore'):
        log_p     = np.log(window_df['modal_price'].replace(0, np.nan)).dropna()
        log_p_ret = log_p.diff(periods=7).dropna()

    if not log_p_ret.empty:
        low_q  = log_p_ret.quantile(0.05)
        high_q = log_p_ret.quantile(0.95)
        clipped  = log_p_ret.clip(lower=low_q, upper=high_q)
        std_frac = float(clipped.std(ddof=0))
        if std_frac == 0 or np.isnan(std_frac):
            std_frac = 1e-6
    else:
        std_frac = 1e-6

    std_frac = min(std_frac, 0.25)
    P_positive = float(stats.norm.cdf((pred / 100.0) / (std_frac + 1e-12)))

    # Elasticity & Context
    arrival_vs_expected_festival_pct = _compute_festival_arrival_metrics(data)

    elasticity = meta.get('rolling_elasticity_30d', 0.0)
    elasticity_type = 'festival' if meta.get('is_festival', 0) == 1 else 'normal'

    stress = meta.get('supply_stress_score', 0.0)
    shock_flag = abs(meta.get('arrival_deviation_pct', 0.0)) > 0.5

    # Lag-peak correlation
    ac = data[['date', 'arrivals_tonnes', 'modal_price']].copy()
    ac['arr_change']   = ac['arrivals_tonnes'].pct_change().fillna(0)
    ac['price_change'] = ac['modal_price'].pct_change().fillna(0)
    max_corr, best_lag = 0.0, 0
    for lag in range(0, 31):
        shifted = ac['arr_change'].shift(lag).fillna(0)
        corr    = float(np.corrcoef(shifted, ac['price_change'])[0, 1]) if len(ac) > 10 else 0.0
        if np.isnan(corr):
            continue
        if abs(corr) > abs(max_corr):
            max_corr, best_lag = corr, lag

    ensemble_log = bundle["metadata"].get("ensemble_log", {})
    errors = bundle["metadata"].get("cv_scores", {})
    confidence = prediction_result["confidence"]

    return AgentOutput(
        agent_name="ArrivalVolume",
        prediction=float(pred),
        confidence=round(confidence, 3),
        metadata={
            "commodity": commodity,
            "mandi": mandi,
            "timestamp": str(datetime.utcnow()),
            "expected_7d_price_change_pct": float(pred),
            "return_std": float(std_frac * 100.0),
            "P_positive": float(P_positive),
            "supply_regime": _supply_regime(stress),
            "supply_stress_score": round(stress, 3),
            "elasticity_coefficient": round(elasticity, 4),
            "elasticity_type": elasticity_type,
            "lag_peak_days": int(best_lag) if best_lag is not None else None,
            "festival_context": {
                'festival': None,
                'days_to_festival': None,
                'arrival_vs_expected_pct': float(arrival_vs_expected_festival_pct),
            },
            "supply_shock_flag": bool(shock_flag),
            "arrival_vs_expected_pct": float(arrival_vs_expected_festival_pct),
            "ensemble_log": ensemble_log,
            "ensemble_model_mapes": errors,
            "n_models_used": len(prediction_result["model_predictions"]),
            "prediction_std": round(prediction_result["prediction_std"], 4),
            "n_models_in_ensemble": bundle["metadata"].get("n_active_models", 0),
            "explainable_features": {
                'commodity': commodity,
                'mandi': mandi,
                'arrival_deviation_pct': float(meta.get('arrival_deviation_pct', 0.0)),
                'arrival_vs_expected_festival_pct': float(arrival_vs_expected_festival_pct),
                'rolling_elasticity_30d': round(elasticity, 4),
                'is_festival_today': bool(meta.get('is_festival', 0) == 1),
                'ensemble_top_model': bundle["metadata"].get("best_model_name", "unknown"),
            }
        },
        model_breakdown={
            name: {
                "prediction": round(float(prediction_result["model_predictions"].get(name, 0.0)), 4),
                "weight": round(w, 4)
            }
            for name, w in prediction_result["normalized_weights"].items()
        }
    )
