import pandas as pd
import numpy as np
from datetime import timedelta, date
from typing import Dict, Any

from data.repository import DataRepository
from core.agents.seasonality_agent import run_seasonality_agent
from core.agents.arrival_volume_agent import run_arrival_volume_agent
from ensemble.meta_ensemble import run_meta_ensemble
from utils.logger import get_logger

logger = get_logger(__name__)

def run_backtest_report(commodity: str, mandi: str, eval_days: int = 60) -> Dict[str, Any]:
    """
    Backtesting & Validation Pipeline for multi-agent price prediction system.
    Evaluates system performance strictly avoiding future data leakage.
    """
    logger.info(f"Starting backtest for {commodity}_{mandi} over last {eval_days} days.")
    
    repo = DataRepository()
    data = repo.get_processed_data(commodity, mandi)
    
    if data.empty:
        raise ValueError(f"No data available for {commodity}_{mandi}")
        
    data['date'] = pd.to_datetime(data['date'])
    data = data.sort_values('date').reset_index(drop=True)
    
    # 1. Define Backtest Loop
    max_date = data['date'].max()
    # Leave 7 days at the end to compute ground truth
    end_eval_date = max_date - timedelta(days=7)
    start_eval_date = end_eval_date - timedelta(days=eval_days - 1)
    
    eval_dates = data[(data['date'] >= start_eval_date) & (data['date'] <= end_eval_date)]['date'].tolist()
    
    if not eval_dates:
        raise ValueError("Not enough historical data for the requested evaluation window.")
        
    # Pre-train models up to start_eval_date to ensure NO future data leakage
    logger.info("Pre-training models up to start_eval_date to avoid data leakage.")
    train_data = data[data['date'] <= start_eval_date].copy()
    
    from core.agents.arrival.training.train_arrival_models import train_arrival_models
    train_arrival_models(train_data, commodity=commodity, mandi=mandi)
    
    from core.agents.seasonality.training.train_seasonality import train_seasonality_models
    train_seasonality_models(train_data, commodity=commodity, mandi=mandi)
        
    results = []
    recent_biases = []
    
    for t in eval_dates:
        t_date = t.date()
        
        # 2. Run Full System
        try:
            # Agents natively slice data up to target_date (no leakage)
            s_out = run_seasonality_agent(commodity, mandi, target_date=t_date)
            a_out = run_arrival_volume_agent(commodity, mandi, target_date=t_date)
            
            fusion = run_meta_ensemble(
                seasonality_output=s_out,
                arrival_output=a_out,
                external_impact=0.0,
                external_confidence=0.0
            )
        except Exception as e:
            logger.warning(f"Failed to run inference for {t_date}: {e}")
            continue
            
        predicted_change = fusion.final_prediction
        confidence = fusion.final_confidence
        
        # Optimization 5: Agent Signal Validation (MANDATORY)
        logger.info(f"Raw Signals for {t_date}: Seasonality={s_out.prediction:.2f}%, Arrival={a_out.prediction:.2f}%, Final={predicted_change:.2f}%")
        
        # Optimization 4: Direction Bias Correction — disabled
        # Bias correction was counterproductive: the persistent positive
        # bias from Seasonality was scaling down negative Arrival predictions
        # and preventing SELL thresholds from being crossed.
        
        # Optimization 1: Adaptive SELL Threshold (capped)
        # Use 7-day return std but cap so high-vol markets still produce SELL signals
        _prices_hist = data[data['date'] <= t]['modal_price']
        _7d_returns = _prices_hist.pct_change(periods=7).dropna().tail(30) * 100.0
        vol_7d = float(_7d_returns.std()) if len(_7d_returns) >= 5 else 5.0
        vol_7d = max(vol_7d, 1.0)
        # Cap threshold at -2.0% so extremely volatile markets can still SELL
        threshold = max(-(0.4 * vol_7d), -2.0)
        # Step 1: Scale threshold by 0.8 to increase SELL sensitivity by ~20-30%
        sell_threshold = 0.8 * threshold
        logger.debug(f"[Threshold] vol_7d={vol_7d:.2f}%, threshold={threshold:.2f}%, sell_threshold={sell_threshold:.2f}%, predicted={predicted_change:.2f}%")
        decision = "SELL" if predicted_change < sell_threshold else "WAIT"
        
        # Optimization 6: Confidence-Based Filtering
        # Step 2: Relaxed from 0.2 → 0.15 to allow more valid signals through
        if confidence < 0.15:
            decision = "WAIT"
        
        # 4. Get Ground Truth
        current_price_row = data[data['date'] == t]
        future_date = t + timedelta(days=7)
        
        future_rows = data[data['date'] >= future_date]
        if future_rows.empty:
            continue
            
        future_price_row = future_rows.iloc[0]
        
        price_t = float(current_price_row['modal_price'].iloc[0])
        price_t7 = float(future_price_row['modal_price'])
        
        if price_t == 0:
            continue
            
        actual_change = ((price_t7 - price_t) / price_t) * 100.0
        
        # Update Bias Tracker
        actual_sign = np.sign(actual_change)
        pred_sign = np.sign(predicted_change)
        recent_biases.append(pred_sign - actual_sign)
        if len(recent_biases) > 30:
            recent_biases.pop(0)
        
        # 5. Compare
        error = predicted_change - actual_change
        abs_error = abs(error)
        
        # 3. Store Prediction
        results.append({
            "date": t_date,
            "predicted_change": predicted_change,
            "actual_change": actual_change,
            "confidence": confidence,
            "decision": decision,
            "error": error,
            "abs_error": abs_error
        })
        
        logger.debug(f"Backtest {t_date}: Pred={predicted_change:.2f}%, Act={actual_change:.2f}%, Dec={decision}")

    if not results:
        raise ValueError("Failed to evaluate any dates. Check data continuity.")
        
    # 7. Metrics
    df_res = pd.DataFrame(results)
    
    # Regression Metrics
    mae = df_res['abs_error'].mean()
    rmse = np.sqrt((df_res['error'] ** 2).mean())
    
    non_zero_actuals = df_res[df_res['actual_change'].abs() > 0.01]
    if not non_zero_actuals.empty:
        mape = (non_zero_actuals['abs_error'] / non_zero_actuals['actual_change'].abs()).mean() * 100.0
    else:
        mape = 0.0

    # Direction Accuracy
    # Filtering out "noisy" flat days (abs change < 0.5%) for a cleaner directional signal
    meaningful_moves = df_res[df_res['actual_change'].abs() > 0.5].copy()
    if not meaningful_moves.empty:
        meaningful_moves['pred_sign'] = np.sign(meaningful_moves['predicted_change'])
        meaningful_moves['actual_sign'] = np.sign(meaningful_moves['actual_change'])
        direction_accuracy = (meaningful_moves['pred_sign'] == meaningful_moves['actual_sign']).mean() * 100.0
    else:
        direction_accuracy = 0.0
    
    
    # Decision Evaluation
    # Was actual_change negative when SELL was signaled?
    sell_signals = df_res[df_res['decision'] == 'SELL']
    if len(sell_signals) > 0:
        # Strict: Actual drop occurred
        sell_accuracy = (sell_signals['actual_change'] < 0).mean() * 100.0
        # Relaxed: No significant rise occurred (actual_change <= 0.5)
        relaxed_sell_accuracy = (sell_signals['actual_change'] <= 0.5).mean() * 100.0
    else:
        sell_accuracy = float('nan')
        relaxed_sell_accuracy = float('nan')
        
    wait_signals = df_res[df_res['decision'] == 'WAIT']
    if len(wait_signals) > 0:
        wait_accuracy = (wait_signals['actual_change'] >= 0).mean() * 100.0
    else:
        wait_accuracy = float('nan')

    # Confidence Calibration
    median_conf = df_res['confidence'].median()
    high_conf = df_res[df_res['confidence'] > median_conf]
    low_conf = df_res[df_res['confidence'] <= median_conf]
    
    # 8. Output Report
    report = {
        "regression_metrics": {
            "mae": mae,
            "rmse": rmse,
            "mape": mape
        },
        "direction_accuracy": direction_accuracy,
        "decision_metrics": {
            "sell_accuracy": sell_accuracy,
            "relaxed_sell_accuracy": relaxed_sell_accuracy,
            "wait_accuracy": wait_accuracy,
            "n_sell_signals": len(sell_signals),
            "n_wait_signals": len(wait_signals)
        },
        "confidence_analysis": {
            "avg_error_high_conf": float(high_conf['abs_error'].mean()) if not high_conf.empty else 0.0,
            "avg_error_low_conf": float(low_conf['abs_error'].mean()) if not low_conf.empty else 0.0,
            "calibration_aligned": bool(
                (not high_conf.empty and not low_conf.empty) and 
                (high_conf['abs_error'].mean() < low_conf['abs_error'].mean())
            )
        }
    }
    
    # 9. Human-Readable Summary
    print("\n" + "="*50)
    print(f"BACKTEST EVALUATION REPORT: {commodity.upper()} - {mandi.upper()}")
    print("="*50)
    print(f"Evaluation Window: {eval_days} days (N={len(df_res)} valid points)")
    print(f"Direction accuracy: {direction_accuracy:.1f}%")
    
    s_acc = report["decision_metrics"]["sell_accuracy"]
    r_s_acc = report["decision_metrics"]["relaxed_sell_accuracy"]
    w_acc = report["decision_metrics"]["wait_accuracy"]
    print(f"SELL accuracy (strict): {s_acc:.1f}% (N={len(sell_signals)})")
    print(f"SELL accuracy (relaxed): {r_s_acc:.1f}%")
    print(f"WAIT accuracy: {w_acc:.1f}% (N={len(wait_signals)})")
    
    calib = "Yes" if report["confidence_analysis"]["calibration_aligned"] else "No"
    print(f"Confidence calibrated: {calib}")
    
    # 10. Diagnostics
    print("\n--- DIAGNOSTICS ---")
    if direction_accuracy < 55.0:
        print("[WARNING] Direction accuracy < 55%. System is struggling to predict trend direction.")
    else:
        print("[OK] Direction accuracy is healthy (>55%).")
        
    if len(sell_signals) > 0 and s_acc < 60.0:
        print("[WARNING] SELL accuracy < 60%. Risk of false positive sell signals.")
    elif len(sell_signals) > 0:
        print("[OK] SELL accuracy is healthy (>60%).")
        
    if not report["confidence_analysis"]["calibration_aligned"]:
        print("[WARNING] Confidence is NOT calibrated. High confidence predictions have worse errors.")
    else:
        print("[OK] Confidence is properly calibrated.")
        
    print("="*50 + "\n")
    
    logger.info(f"Backtest Complete. Direction Acc: {direction_accuracy:.1f}%, MAE: {mae:.2f}%")
    return report

if __name__ == "__main__":
    import json
    # Test execution
    res = run_backtest_report("tomato", "kolar", eval_days=60)
    print(json.dumps(res, indent=2))
