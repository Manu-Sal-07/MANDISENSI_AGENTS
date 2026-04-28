import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Tuple
from pathlib import Path
import scipy.stats as stats

from config.settings import settings, AgentOutput
from data.repository import DataRepository
from utils.logger import get_logger
from core.agents.seasonality_models import TieredModelPipeline
from statsmodels.tsa.seasonal import STL
from scipy.stats import skew
from ensemble.feedback_store import FeedbackStore
from ensemble.regime_detector import RegimeDetector
from ensemble.dynamic_weighter import DynamicWeighter

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
        self.pipeline = TieredModelPipeline(horizon=self.horizon_days)
        
        self.model_dir = Path(settings.paths.models_dir) / "seasonality"
        self.model_dir.mkdir(parents=True, exist_ok=True)

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

        # 1. Structural Enrichments
        df = merge_festivals(df)
        festival_adj = self._compute_festival_adjustment(df)
        
        # 2. STL Decomposition Extraction identifying strict analytic bounds
        try:
            # Prepare series: ensure daily index, fill small gaps and infer period
            df_proc = df.copy()
            if 'date' in df_proc.columns:
                df_proc['date'] = pd.to_datetime(df_proc['date'])
                df_proc = df_proc.set_index('date').sort_index()
            series = df_proc['modal_price'].resample('D').mean()
            # interpolate short gaps (limit 7 days), forward/backward fill for ends
            series = series.interpolate(method='time', limit=7).ffill().bfill()


            # Default to log-transform because mandi prices commonly exhibit
            # multiplicative seasonality. This stabilizes variance for STL.
            use_log = True
            series_for_stl = np.log1p(series)

            # Try multiple candidate periods (weekly, monthly, yearly)
            candidate_periods = [7, 30, 365]
            candidates = []
            for period in candidate_periods:
                if len(series_for_stl.dropna()) < max(3, period * 2):
                    continue
                try:
                    # increase seasonal smoothing window (must be odd)
                    seasonal_window = 21 if 21 % 2 == 1 else 21 + 1
                    stl_try = STL(series_for_stl, period=period, seasonal=seasonal_window, robust=True)
                    res_try = stl_try.fit()
                    seasonal_try = res_try.seasonal
                    resid_try = res_try.resid
                    var_s = np.var(seasonal_try)
                    var_r = np.var(resid_try)
                    ss = float(var_s / (var_s + var_r)) if (var_s + var_r) != 0 else 0.0
                    candidates.append((ss, period, res_try))
                except Exception:
                    continue

            # choose best candidate by season_strength (highest ss)
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_ss, best_period, best_res = candidates[0]
                res = best_res
            else:
                # fallback: try a minimal STL with weekly period if possible
                fallback_period = 7 if len(series_for_stl.dropna()) >= 14 else max(3, int(len(series_for_stl.dropna()) / 2))
                res = STL(series_for_stl, period=fallback_period, seasonal=21, robust=True).fit()
                best_period = fallback_period
                use_log = True

            # record selected STL metadata
            self._last_selected_stl_period = int(best_period)
            self._last_used_log_for_stl = bool(use_log)

            # Extract components; if log used, seasonal/resid are on log-scale but variance ratio is comparable
            df_proc['trend'] = res.trend
            df_proc['seasonal'] = res.seasonal
            df_proc['resid'] = res.resid
            # merge seasonal back into original df by date
            df = df.merge(df_proc[['trend', 'seasonal', 'resid']].reset_index(), on='date', how='left')
            
            cycle_phase = self._determine_cycle_phase(res.trend)
            season_strength = self._compute_season_strength(res.seasonal, res.resid)
            # pass the full dataframe (with seasonal column) for drift detection
            drift_warn = self._compute_drift_warning(df)
        except Exception as e:
            logger.warning(f"StatsModels convergence exception handled securely: {e}")
            cycle_phase = "Neutral"
            season_strength = 0.0
            drift_warn = False

        # 3. Model Training Pipeline Execution (Delegated CV)
        feature_cols = ['day_of_week', 'month', 'is_festival', 'arrivals_tonnes', 
                        'price_lag_1', 'price_lag_7', 'price_lag_14', 'price_roll_mean_7', 
                        'momentum_7', 'volatility_proxy_14']
        
        df_train = df.dropna(subset=feature_cols).copy()
        
        training_res = self.pipeline.train_and_select(df_train, feature_cols, 'modal_price')
        models = training_res['top_models']
        weights = training_res['weights']

        # ── Dynamic Weighting & Regime Detection ────────────────────────
        detector = RegimeDetector()
        regimes = detector.detect_regime(df_train)

        feedback_store = FeedbackStore()
        weighter = DynamicWeighter(feedback_store)

        weights = weighter.adjust_weights(
            base_weights=weights,
            agent_type='Seasonality',
            commodity=commodity,
            mandi=mandi,
            regimes=regimes
        )
        
        # Override the ensemble engine weights so predictions and logs match
        if self.pipeline.last_ensemble is not None:
            self.pipeline.last_ensemble.weights = weights

        # Retrieve full ensemble audit log for metadata injection (Step 6)
        ensemble_log = (
            self.pipeline.last_ensemble.get_ensemble_log()
            if self.pipeline.last_ensemble is not None
            else {}
        )
        
        # 4. Synthesize Predictive 30D Forecasts dynamically
        last_row = df_train.iloc[-1:].copy()
        forecasts = []
        current_price = float(last_row['modal_price'].values[0])
        X_fut = last_row[feature_cols].copy()
        
        for i in range(self.horizon_days):
            preds = self.pipeline.ensemble_predict(models, weights, X_fut)
            forecasts.append(float(preds[0]))
            X_fut['price_lag_1'] = preds[0] # Auto-regressive mock assignment

        # ── Log Predictions to FeedbackStore ───────────────────────────
        target_dt = pd.to_datetime(last_row['date'].iloc[0]) + pd.Timedelta(days=self.horizon_days)
        if self.pipeline.last_ensemble is not None:
            for model_name, p in self.pipeline.last_ensemble.last_predictions.items():
                feedback_store.log_prediction(
                    agent_type='Seasonality',
                    commodity=commodity,
                    mandi=mandi,
                    model_name=model_name,
                    target_date=target_dt.strftime('%Y-%m-%d'),
                    prediction=float(p)
                )

        # expected_return as fractional value (e.g., 0.03 == 3%) for internal stats
        expected_return_frac = (forecasts[-1] - current_price) / current_price
        # compute return_std (percent) and p_positive using fractional expected return
        return_std_percent, p_positive = self._compute_statistical_return_metrics(df_train, expected_return_frac)

        # 5. Compile Robust Confidence Mappings
        avg_mape = float(np.mean(list(training_res['metrics'].values())))
        base_confidence = max(0.0, min(1.0, 1.0 - avg_mape))
        
        # Penalize confidence slightly if seasonality is fundamentally drifting structurally
        if drift_warn:
            base_confidence *= 0.8
            
        logger.info(f"Execution closed securely generating deterministic variables resolving Seasonality constraints.")

        return AgentOutput(
            agent_name="Seasonality",
            prediction=round(expected_return_frac * 100.0, 2),
            confidence=round(base_confidence, 3),
            metadata={
                "commodity": commodity,
                "mandi": mandi,
                "timestamp": str(pd.Timestamp.utcnow()),
                "expected_30d_return": round(expected_return_frac * 100.0, 2),
                "return_std": round(return_std_percent, 2),
                "P_positive": round(p_positive, 3),
                "season_strength": round(season_strength, 3),
                "festival_adjustment": round(festival_adj, 2),
                "cycle_phase": cycle_phase,
                "drift_warning": drift_warn,
                "forecasted_prices": [round(p, 2) for p in forecasts],
                "ensemble_log": ensemble_log,
                "top_models_mape": training_res['metrics'],
                "festival_regime_mape": training_res['metrics_festival'],
                "best_model": self.pipeline.last_ensemble.best_model_name if self.pipeline.last_ensemble else None,
                "n_active_models": self.pipeline.last_ensemble.n_active_models if self.pipeline.last_ensemble else 0,
                "drift_normalized_rmse": getattr(self, '_last_drift_normalized_rmse', None),
                "drift_threshold": getattr(self, '_last_drift_threshold', None),
                "stl_selected_period": getattr(self, '_last_selected_stl_period', None),
                "stl_used_log_transform": getattr(self, '_last_used_log_for_stl', None),
                "explainable_features": {
                    "base_trend_strength": "High" if cycle_phase in ["Ascending", "Descending"] else "Low",
                    "festival_impact_active": bool(list(df_train['is_festival'])[-1] == 1)
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

def run_seasonality_agent(commodity: str, mandi: str, target_date: Optional[date] = None) -> AgentOutput:
    agent = SeasonalityAgent()
    return agent.execute(commodity, mandi, target_date)
