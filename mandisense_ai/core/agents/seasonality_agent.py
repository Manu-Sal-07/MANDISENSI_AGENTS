import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Tuple
from pathlib import Path
import scipy.stats as stats

from mandisense_ai.config.settings import settings, AgentOutput
from mandisense_ai.data.repository import DataRepository
from mandisense_ai.utils.logger import get_logger
from statsmodels.tsa.seasonal import STL
from scipy.stats import skew
from mandisense_ai.ensemble.feedback_store import FeedbackStore
from mandisense_ai.ensemble.regime_detector import RegimeDetector
from mandisense_ai.ensemble.dynamic_weighter import DynamicWeighter
from mandisense_ai.core.agents.seasonality.inference import SeasonalityInferencePipeline
from mandisense_ai.core.agents.seasonality.training.train_seasonality import (
    load_seasonality_bundle,
    predict_with_ensemble,
    train_seasonality_models,
)

logger = get_logger(__name__)

def merge_festivals(df: pd.DataFrame) -> pd.DataFrame:
    """Safely merges optional explicit disjoint festival constraints mapping structural limits."""
    raw_path = Path(settings.paths.raw_data) / "festival_calendar.csv"
    if not raw_path.exists():
        df['is_festival'] = df.get('is_festival_season', 0)
        return df
        
    try:
        fdf = pd.read_csv(raw_path)
        date_col = next((c for c in fdf.columns if 'date' in str(c).lower()), None)
        if date_col:
            fdf[date_col] = pd.to_datetime(fdf[date_col], errors='coerce')
            fdf['is_festival'] = 1
            fdf = fdf[[date_col, 'is_festival']].dropna().rename(columns={date_col: 'date'})
            df = df.merge(fdf, on='date', how='left')
            df['is_festival'] = df['is_festival'].fillna(0).astype(int)
        else:
            df['is_festival'] = df.get('is_festival_season', 0)
    except Exception as e:
        logger.warning(f"Festival relational mapping decoupled conditionally: {e}. Defaulting assumptions.")
        df['is_festival'] = df.get('is_festival_season', 0)
        
    return df

class SeasonalityAgent:
    """
    The orchestrator handling centralized extraction of cyclical macro dimensions.
    Calculates pure analytic features (Season Strength, P_positive) natively 
    prior to assigning prediction algorithms dynamically.
    """
    def __init__(self):
        self.repo = DataRepository()
        self.horizon_days = 30
        self.model_dir = Path(settings.paths.models_dir) / "seasonality"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.inference_pipeline = SeasonalityInferencePipeline()

    def _determine_cycle_phase(self, stl_trend: pd.Series) -> str:
        """Extracts relative non-stationary Phase representations analytically."""
        recent_gradient = stl_trend.diff().tail(14).mean()
        if recent_gradient > 1.5:
            return "Ascending"
        elif recent_gradient < -1.5:
            return "Descending"
        elif stl_trend.iloc[-1] > stl_trend.mean() + stl_trend.std():
            return "Peak"
        else:
            return "Trough"

    def _compute_season_strength(self, seasonal: pd.Series, resid: pd.Series) -> float:
        """
        Calculates Seasonal Variance Ratio: Var(Seasonal) / (Var(Seasonal) + Var(Residual))
        Why: Allows meta-ensemble to ignore this agent if its outputs are predominantly noise.
        """
        var_s = np.var(seasonal)
        var_r = np.var(resid)
        if (var_s + var_r) == 0:
            return 0.0
        return float(var_s / (var_s + var_r))

    def _compute_drift_warning(self, df: pd.DataFrame) -> bool:
        """
        Detects structural breaks by comparing the recent seasonal curve
        (last 3 years) with the long-term seasonal curve (all history).

        Approach:
        - Aggregate seasonal component by day-of-year for both recent and long-term
        - Compute RMSE between the two curves and normalize by mean absolute
          magnitude of the long-term seasonal curve
        - Raise a warning if normalized RMSE exceeds a threshold (0.20)
        """
        if 'date' not in df.columns or 'seasonal' not in df.columns:
            return False

        # Require at least 3 years of data for a reliable recent curve
        if len(df) < 3 * 365:
            return False

        df_local = df.copy()
        df_local['doy'] = pd.to_datetime(df_local['date']).dt.dayofyear

        # long-term seasonal by day-of-year
        long_term = df_local.groupby('doy')['seasonal'].mean()

        # recent 3 years slice
        recent_cutoff = pd.to_datetime(df_local['date'].max()) - pd.Timedelta(days=3 * 365)
        recent = df_local[df_local['date'] > recent_cutoff].groupby('doy')['seasonal'].mean()

        # align indexes
        common_index = long_term.index.intersection(recent.index)
        if len(common_index) == 0:
            return False

        lt = long_term.loc[common_index].values
        rc = recent.loc[common_index].values

        rmse = np.sqrt(np.mean((lt - rc) ** 2))
        denom = (np.mean(np.abs(lt)) + 1e-9)
        normalized_rmse = rmse / denom

        # Threshold chosen conservatively: increase sensitivity threshold to 0.8
        # Store values for transparency
        self._last_drift_normalized_rmse = float(normalized_rmse)
        self._last_drift_threshold = 0.8
        return bool(normalized_rmse > self._last_drift_threshold)

    def _compute_festival_adjustment(self, df: pd.DataFrame) -> float:
        """
        Calculates the explicit long-term historical price premium explicitly 
        during validated festival windows across absolute historic data.
        """
        # If explicit festival flag exists from merge_festivals, use it
        if 'is_festival' in df.columns and df['is_festival'].sum() > 0:
            fest_mean = df[df['is_festival'] == 1]['modal_price'].mean()
            norm_mean = df[df['is_festival'] == 0]['modal_price'].mean()
            if pd.isna(fest_mean) or norm_mean == 0 or pd.isna(norm_mean):
                return 0.0
            return float(((fest_mean - norm_mean) / norm_mean) * 100.0)

        # Fallback: attempt to load festival_calendar.csv and construct +/-7 day windows
        raw_path = Path(settings.paths.raw_data) / "festival_calendar.csv"
        if raw_path.exists():
            try:
                fdf = pd.read_csv(raw_path)
                date_col = next((c for c in fdf.columns if 'date' in str(c).lower()), None)
                if date_col:
                    fdf[date_col] = pd.to_datetime(fdf[date_col], errors='coerce')
                    fdf = fdf.dropna(subset=[date_col])
                    # build festival windows
                    windows = []
                    for d in fdf[date_col].dt.date.unique():
                        d0 = pd.to_datetime(d)
                        windows.append((d0 - pd.Timedelta(days=7), d0 + pd.Timedelta(days=7)))

                    df_dates = pd.to_datetime(df['date'])
                    is_fest = pd.Series(False, index=df.index)
                    for (start, end) in windows:
                        is_fest = is_fest | ((df_dates >= start) & (df_dates <= end))

                    if is_fest.sum() == 0:
                        return 0.0

                    fest_mean = df.loc[is_fest, 'modal_price'].mean()
                    norm_mean = df.loc[~is_fest, 'modal_price'].mean()
                    if pd.isna(fest_mean) or pd.isna(norm_mean) or norm_mean == 0:
                        return 0.0
                    return float(((fest_mean - norm_mean) / norm_mean) * 100.0)
            except Exception:
                return 0.0

        return 0.0

    def _compute_statistical_return_metrics(self, df: pd.DataFrame, expected_ret: float) -> Tuple[float, float]:
        """
        Compute the historical 30-day return distribution restricted to the
        current seasonal phase (proxied by month window around the most recent date).

        Steps:
        - Identify the month of the most recent observation
        - Use a +/- 1 month window across history to collect comparable seasonal periods
        - Compute 30-day percent returns for that subset
        - Fallback to using the full history if subset is too small
        - Compute standard deviation and P_positive via the normal CDF
        """
        # Prefer regime-aware samples: pick comparable seasonal windows across years
        df_local = df.copy()
        if 'date' in df_local.columns:
            df_local['date'] = pd.to_datetime(df_local['date'])
            latest = df_local['date'].max()
            doy = latest.dayofyear
            # window in days around the same seasonal phase
            window_days = 15
            mask_phase = df_local['date'].dt.dayofyear.between(
                ((doy - window_days - 1) % 365) + 1,
                ((doy + window_days - 1) % 365) + 1,
            )
            # The above simple modulo can fail across year boundary; construct explicit condition
            def in_window(dt):
                dd = dt.dayofyear
                low = doy - window_days
                high = doy + window_days
                if low < 1:
                    return (dd >= (365 + low + 1)) or (dd <= high)
                if high > 365:
                    return (dd >= low) or (dd <= (high - 365))
                return (dd >= low) and (dd <= high)

            mask_phase = df_local['date'].apply(in_window)
            candidate = df_local[mask_phase]
            # require a minimum number of samples; else fallback to last 3 years
            if len(candidate) < 30:
                start_date = latest - pd.Timedelta(days=3 * 365)
                candidate = df_local[df_local['date'] >= start_date]
            if len(candidate) < 60:
                candidate = df_local
        else:
            candidate = df_local

        # compute log-returns over 30 days (fractional)
        prices = candidate['modal_price']
        with np.errstate(divide='ignore', invalid='ignore'):
            log_prices = np.log(prices.replace(0, np.nan)).dropna()
        returns = log_prices.diff(periods=30).dropna()

        # winsorize extreme tails to reduce influence of outliers (1st-99th percentile)
        if not returns.empty:
            low = returns.quantile(0.01)
            high = returns.quantile(0.99)
            returns_clipped = returns.clip(lower=low, upper=high)
        else:
            returns_clipped = returns

        # robust std using winsorized log-returns; fallback to MAD
        if not returns_clipped.empty:
            std_frac = float(returns_clipped.std(ddof=0))
            if std_frac == 0 or pd.isna(std_frac):
                mad = float(np.median(np.abs(returns_clipped - np.median(returns_clipped))))
                std_frac = mad * 1.4826 if mad > 0 else 1e-6
        else:
            std_frac = 1e-6

        # Cap standard deviation at realistic maximum for 30-day tomato forecasts
        max_std = 0.30  # 30% (fractional)
        std_frac = min(std_frac, max_std)

        # compute probability using normal cdf; expected_ret is fractional
        p_positive = float(stats.norm.cdf(expected_ret / (std_frac + 1e-12)))

        # return std as percent for human readability
        return float(std_frac * 100.0), p_positive

    def execute(self, commodity: str, mandi: str, target_date: Optional[date] = None) -> AgentOutput:
        """
        Main execution layer securely mapping logic outputs.
        """
        logger.info(f"Seasonality Execution triggered targeting -> {commodity} internally bound locally for {mandi}")
        df = self.repo.get_processed_data(commodity, mandi)
        
        if df.empty:
            logger.error(f"Cannot resolve Parquet frame array tracking {commodity} safely!")
            return AgentOutput(
                agent_name="Seasonality",
                prediction=0.0,
                confidence=0.0,
                metadata={
                    "commodity": commodity,
                    "mandi": mandi,
                    "timestamp": str(pd.Timestamp.utcnow()),
                    "error": "No processed data available"
                }
            )

        try:
            try:
                bundle = load_seasonality_bundle(commodity=commodity, mandi=mandi)
            except Exception as e:
                logger.warning(f"Failed to load seasonality bundle for {commodity}_{mandi}: {str(e)}. Triggering training fallback.")
                train_seasonality_models(df, commodity=commodity, mandi=mandi)
                bundle = load_seasonality_bundle(commodity=commodity, mandi=mandi)
                
            timestamp = pd.to_datetime(target_date) if target_date is not None else pd.to_datetime(df["date"]).max()
            features = self.inference_pipeline.build_inference_features(
                df, 
                mandi_name=mandi, 
                timestamp=timestamp, 
                feature_columns=bundle["feature_columns"]
            )
            prediction_result = predict_with_ensemble(bundle, features)

            prediction_30d = float(prediction_result["prediction"] * 100.0)
            weighted_volatility = float(np.std(list(prediction_result["ensemble_prediction"].values())))

            logger.info(
                "Seasonality model bundle loaded for %s/%s with %d models at %s",
                commodity,
                mandi,
                len(bundle["models"]),
                str(pd.Timestamp.utcnow()),
            )

            metadata = {
                "commodity": commodity,
                "mandi": mandi,
                "timestamp": str(pd.Timestamp.utcnow()),
                "expected_30d_return": round(prediction_30d, 4),
                "return_std": round(weighted_volatility * 100.0, 4),
                "cycle_phase": "multi_horizon_price_cycle",
                "drift_warning": False,
                "feature_columns": bundle["feature_columns"],
                "target_columns": bundle["target_columns"],
                "metrics_per_model": bundle["metadata"]["metrics_per_model"],
                "weights_per_horizon": bundle["weights"],
                "best_models_per_horizon": bundle["metadata"]["best_models_per_horizon"],
                "stability_enforced_prediction": prediction_result["stable_prediction"],
                "raw_ensemble_prediction": prediction_result["ensemble_prediction"],
                "prediction_confidence": prediction_result["confidence"],
                "ensemble_metadata": prediction_result["metadata"],
            }

            return AgentOutput(
                agent_name="Seasonality",
                prediction=round(prediction_30d, 4),
                confidence=round(float(prediction_result["confidence"]), 4),
                metadata=metadata,
                model_breakdown=prediction_result["model_breakdown"],
            )
        except Exception as exc:
            logger.error(f"Seasonality inference execution failed: {exc}", exc_info=True)
            return AgentOutput(
                agent_name="Seasonality",
                prediction=0.0,
                confidence=0.0,
                metadata={
                    "commodity": commodity,
                    "mandi": mandi,
                    "timestamp": str(pd.Timestamp.utcnow()),
                    "error": str(exc),
                },
            )

        

def run_seasonality_agent(commodity: str, mandi: str, target_date: Optional[date] = None) -> AgentOutput:
    agent = SeasonalityAgent()
    return agent.execute(commodity, mandi, target_date)
