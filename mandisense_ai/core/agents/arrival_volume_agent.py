"""Arrival Volume Agent

Reuses Phase 1 processed data pipeline, implements festival vs arrival
separation logic, and returns the unified `AgentOutput` model so outputs
are compatible with the meta-ensemble.

Ensemble upgrade (Step 2):
  The single XGBoost model has been replaced by an 8-model ensemble pool
  defined in core/agents/arrival/models/.  A shared ArrivalModelPipeline
  (mirroring TieredModelPipeline) runs TimeSeriesSplit CV on all models,
  computes inverse-MAPE weights, and produces a weighted ensemble prediction.
  The `model_contributions` field in AgentOutput now reflects all 8 model
  weights rather than a fixed {"XGBoost": 1.0}.
"""

import copy
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import scipy.stats as stats

from config.settings import settings, AgentOutput
from data.repository import DataRepository
from utils.logger import get_logger
from core.agents.seasonality_agent import merge_festivals

# ── New: arrival model registry ───────────────────────────────────────────────
from core.agents.arrival.models import ARRIVAL_MODEL_REGISTRY
from ensemble.agent_ensemble import AgentEnsemble
from ensemble.feedback_store import FeedbackStore
from ensemble.regime_detector import RegimeDetector
from ensemble.dynamic_weighter import DynamicWeighter

logger = get_logger(__name__)


# ── Festival helper (unchanged) ───────────────────────────────────────────────
def _safe_days_to_festival(df: pd.DataFrame, ref_date: pd.Timestamp):
    raw_path = Path(settings.paths.raw_data) / "festival_calendar.csv"
    if not raw_path.exists():
        return None, None, None
    try:
        fdf = pd.read_csv(raw_path)
        date_col = next((c for c in fdf.columns if 'date' in str(c).lower()), None)
        name_col = next((c for c in fdf.columns if 'name' in str(c).lower()), None)
        if date_col:
            fdf[date_col] = pd.to_datetime(fdf[date_col], errors='coerce')
            fdf = fdf.dropna(subset=[date_col])
            future = fdf[fdf[date_col] >= ref_date]
            if future.empty:
                return None, None, None
            next_f = future.sort_values(date_col).iloc[0]
            fest_name = next_f[name_col] if name_col and name_col in fdf.columns else None
            days = (pd.to_datetime(next_f[date_col]) - ref_date).days
            return fest_name, days, next_f[date_col]
    except Exception:
        return None, None, None
# ── ArrivalVolumeAgent ────────────────────────────────────────────────────────
class ArrivalVolumeAgent:
    """Arrival Volume Agent (Phase 3 — Ensemble Edition)

    Predicts short-term price moves driven by arrival volumes using an
    8-model ensemble instead of a single XGBoost.  All other logic
    (feature engineering, elasticity, supply stress, festival metrics)
    is unchanged to preserve backward compatibility.
    """

    def __init__(self):
        self.repo     = DataRepository()

    # ------------------------------------------------------------------ #
    def _feature_engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        d['date'] = pd.to_datetime(d['date'])
        d = d.sort_values('date').reset_index(drop=True)

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

    # ------------------------------------------------------------------ #
    def _compute_festival_arrival_metrics(self, df: pd.DataFrame) -> float:
        df = merge_festivals(df)
        if 'is_festival' in df.columns and df['is_festival'].sum() > 0:
            fest_mean = df.loc[df['is_festival'] == 1, 'arrivals_tonnes'].mean()
            base_mean = df.loc[df['is_festival'] == 0, 'arrivals_tonnes'].mean()
            if pd.notna(fest_mean) and pd.notna(base_mean) and base_mean != 0:
                return float((fest_mean - base_mean) / (base_mean + 1e-9) * 100.0)
        return 0.0

    # ------------------------------------------------------------------ #
    def _supply_regime(self, row: dict) -> str:
        score = row.get('supply_stress_score', 0.0)
        if score > 0.8:   return 'Squeeze'
        if score > 0.6:   return 'Tightening'
        if score < 0.2:   return 'Oversupply'
        return 'Normal'

    # ------------------------------------------------------------------ #
    def train_and_predict(
        self,
        commodity: str,
        mandi:     str,
        target_date: Optional[date] = None,
    ) -> AgentOutput:
        logger.info(f"ArrivalVolume Ensemble Execution → {commodity} @ {mandi}")
        df = self.repo.get_processed_data(commodity, mandi)

        if df.empty:
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

        df = df.sort_values('date').reset_index(drop=True)
        df = merge_festivals(df)

        # ── Feature engineering ────────────────────────────────────────
        df_fe = self._feature_engineer(df)

        # Target: 7-day forward price change %
        df_fe['future_price_7d'] = df_fe['modal_price'].shift(-7)
        df_fe['target_7d_pct']   = (
            (df_fe['future_price_7d'] - df_fe['modal_price'])
            / (df_fe['modal_price'] + 1e-9) * 100.0
        )

        arrival_vs_expected_festival_pct = self._compute_festival_arrival_metrics(df_fe)

        # Supply stress composite
        df_fe['dev_score']      = np.tanh(np.abs(df_fe['arrival_deviation_pct'].fillna(0)))
        df_fe['yoy_score']      = np.tanh(np.abs(df_fe['arrival_yoy_deviation_pct'].fillna(0)))
        df_fe['momentum_score'] = np.tanh(
            np.abs(df_fe['supply_momentum_slope'].fillna(0)
                   / (df_fe['arrivals_30d_mean'] + 1e-9))
        )
        df_fe['supply_stress_score'] = (
            df_fe['dev_score'] * 0.45
            + df_fe['yoy_score'] * 0.35
            + df_fe['momentum_score'] * 0.2
        ).clip(0, 1)

        # Drop rows without a valid target
        df_model = df_fe.dropna(subset=['target_7d_pct']).copy()

        # ── Feature columns (same set for ALL models) ──────────────────
        feature_cols = [
            'arrivals_7d_mean', 'arrivals_30d_mean', 'arrival_deviation_pct',
            'arrival_yoy_deviation_pct', 'consecutive_decline_days',
            'supply_momentum_slope',
            'arrivals_lag_1', 'arrivals_lag_7', 'price_lag_1', 'price_lag_7',
            'rolling_elasticity_30d', 'is_festival',
        ]

        df_model = df_model[feature_cols + ['target_7d_pct', 'date', 'modal_price',
                                             'arrivals_tonnes', 'supply_stress_score']]
        df_model = df_model.fillna(0)

        # ── Ensemble training ──────────────────────────────────────────
        ensemble = AgentEnsemble(
            models=ARRIVAL_MODEL_REGISTRY,
            n_splits=5,
            top_n=8
        )
        ensemble.fit(
            df_model[feature_cols],
            df_model['target_7d_pct'],
            regime_flags=df_model['is_festival'] if 'is_festival' in df_model.columns else None
        )

        # ── Dynamic Weighting & Regime Detection ────────────────────────
        detector = RegimeDetector()
        regimes = detector.detect_regime(df_model)

        feedback_store = FeedbackStore()
        weighter = DynamicWeighter(feedback_store)

        ensemble.weights = weighter.adjust_weights(
            base_weights=ensemble.weights,
            agent_type='ArrivalVolume',
            commodity=commodity,
            mandi=mandi,
            regimes=regimes
        )

        # ── Ensemble prediction on last row ────────────────────────────
        last_row = df_model.iloc[-1:]
        X_last   = last_row[feature_cols]
        pred     = float(ensemble.predict(X_last)[0])
        
        # ── Log Predictions to FeedbackStore ───────────────────────────
        target_dt = pd.to_datetime(last_row['date'].iloc[0]) + pd.Timedelta(days=7)
        for model_name, p in ensemble.last_predictions.items():
            feedback_store.log_prediction(
                agent_type='ArrivalVolume',
                commodity=commodity,
                mandi=mandi,
                model_name=model_name,
                target_date=target_dt.strftime('%Y-%m-%d'),
                prediction=float(p)
            )

        models  = ensemble._fitted_models
        weights = ensemble.weights
        ensemble_log = ensemble.get_ensemble_log()

        # ── Return std & P_positive ─────────────────────────────────────
        latest = pd.to_datetime(df['date'].max())
        mask   = []
        for y_ in range(1, 6):
            try:
                dt_prev = latest - pd.DateOffset(years=y_)
            except Exception:
                dt_prev = latest - pd.Timedelta(days=365 * y_)
            low_  = dt_prev - pd.Timedelta(days=15)
            high_ = dt_prev + pd.Timedelta(days=15)
            mask.append(
                (pd.to_datetime(df['date']) >= low_)
                & (pd.to_datetime(df['date']) <= high_)
            )

        if mask:
            mask_all = mask[0]
            for m in mask[1:]:
                mask_all = mask_all | m
            window_df = df[mask_all]
        else:
            window_df = df

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

        # ── Elasticity ──────────────────────────────────────────────────
        df_prices  = df[['date', 'modal_price', 'arrivals_tonnes']].copy()
        df_prices['date'] = pd.to_datetime(df_prices['date'])
        recent_cut = df_prices.tail(180)
        with np.errstate(divide='ignore', invalid='ignore'):
            lp = np.log(recent_cut['modal_price'].replace(0, np.nan)).dropna()
            la = np.log(recent_cut['arrivals_tonnes'].replace(0, np.nan)).dropna()
        elasticity = 0.0
        if len(lp) >= 10 and len(la) >= 10:
            try:
                lr  = LinearRegression()
                idx = lp.index.intersection(la.index)
                X_e = la.loc[idx].values.reshape(-1, 1)
                y_e = lp.loc[idx].values
                if len(X_e) >= 10:
                    lr.fit(X_e, y_e)
                    elasticity = float(lr.coef_[0])
            except Exception:
                elasticity = float(last_row['rolling_elasticity_30d'].iloc[0]) \
                    if 'rolling_elasticity_30d' in last_row else 0.0

        elasticity_type = 'festival' if bool(last_row['is_festival'].iloc[0] == 1) else 'normal'

        # ── Supply stress (last row) ────────────────────────────────────
        dev      = abs(last_row['arrival_deviation_pct'].iloc[0]) \
            if 'arrival_deviation_pct' in last_row else 0.0
        cons     = float(last_row['consecutive_decline_days'].iloc[0]) \
            if 'consecutive_decline_days' in last_row else 0.0
        cons_norm = min(cons / 30.0, 1.0)
        mom      = abs(float(last_row['supply_momentum_slope'].iloc[0])) \
            if 'supply_momentum_slope' in last_row else 0.0
        mom_norm  = mom / (last_row['arrivals_30d_mean'].iloc[0] + 1e-9)
        stress    = float(np.clip(
            0.5 * np.tanh(dev) + 0.3 * cons_norm + 0.2 * np.tanh(mom_norm), 0.0, 1.0
        ))

        shock_flag = abs(last_row['arrival_deviation_pct'].iloc[0]) > 0.5

        # ── Lag-peak correlation ────────────────────────────────────────
        ac = df[['date', 'arrivals_tonnes', 'modal_price']].copy()
        ac['arr_change']   = ac['arrivals_tonnes'].pct_change().fillna(0)
        ac['price_change'] = ac['modal_price'].pct_change().fillna(0)
        max_corr, best_lag = 0.0, 0
        for lag in range(0, 31):
            shifted = ac['arr_change'].shift(lag).fillna(0)
            corr    = float(np.corrcoef(shifted, ac['price_change'])[0, 1]) \
                if len(ac) > 10 else 0.0
            if np.isnan(corr):
                continue
            if abs(corr) > abs(max_corr):
                max_corr, best_lag = corr, lag

        # ── Confidence: penalise if avg ensemble MAPE is poor ──────────
        avg_mape   = float(np.mean(list(ensemble.errors.values()))) \
            if ensemble.errors else 1.0
        confidence = float(np.clip(1.0 - avg_mape, 0.3, 0.95))

        # ── Build AgentOutput ──────────────────────────────────────────
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
                "supply_regime": self._supply_regime({'supply_stress_score': stress}),
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
                "ensemble_model_mapes": ensemble.errors,
                "n_models_in_ensemble": ensemble.n_active_models,
                "explainable_features": {
                    'commodity': commodity,
                    'mandi': mandi,
                    'arrival_deviation_pct': float(last_row['arrival_deviation_pct'].iloc[0]) if 'arrival_deviation_pct' in last_row else 0.0,
                    'arrival_vs_expected_festival_pct': float(arrival_vs_expected_festival_pct),
                    'rolling_elasticity_30d': round(elasticity, 4),
                    'is_festival_today': bool(last_row['is_festival'].iloc[0] == 1),
                    'ensemble_top_model': ensemble.best_model_name if ensemble.best_model_name else 'unknown',
                }
            },
            model_breakdown={
                name: {
                    "prediction": float(ensemble_log.get("last_predictions", {}).get(name, 0.0)
                                        if isinstance(ensemble_log.get("last_predictions", {}).get(name), (int, float))
                                        else 0.0),
                    "weight": round(w, 4)
                }
                for name, w in weights.items()
            }
        )


# ── Module-level entry point ───────────────────────────────────────────────────
def run_arrival_volume_agent(
    commodity: str, mandi: str, target_date: Optional[date] = None
) -> AgentOutput:
    agent = ArrivalVolumeAgent()
    return agent.train_and_predict(commodity, mandi, target_date)
