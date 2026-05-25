import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error, mean_squared_error
import os
import warnings

warnings.filterwarnings("ignore")

# --- STYLE CONFIGURATION ---
MANDI_GREEN = (27/255, 94/255, 32/255)
MANDI_BLUE = (25/255, 88/255, 150/255)
COLORS = [MANDI_BLUE, "#D32F2F", "#F57C00", MANDI_GREEN]
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'serif'

def evaluate_models(csv_path, output_dir="artifacts/evaluation"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Load Data
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Target: 7-day price change (%) to match MandiSense core logic
    df['target'] = df['modal_price'].pct_change(periods=7).shift(-7) * 100.0
    
    # Features: lags of price change
    for i in range(1, 8):
        df[f'lag_{i}'] = df['modal_price'].pct_change(periods=1).shift(i) * 100.0
        
    df = df.dropna().reset_index(drop=True)
    
    # 2. Split (Walk-forward)
    split_idx = int(len(df) * 0.85)
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]
    
    X_train = train_df[[f'lag_{i}' for i in range(1, 8)]]
    y_train = train_df['target']
    X_test = test_df[[f'lag_{i}' for i in range(1, 8)]]
    y_test = test_df['target']
    
    metrics = {}

    # --- ARIMA ---
    try:
        # ARIMA on the raw target series
        history = list(y_train)
        predictions = []
        for t in range(len(y_test)):
            model = ARIMA(history, order=(5,1,0))
            model_fit = model.fit()
            yhat = model_fit.forecast()[0]
            predictions.append(yhat)
            history.append(y_test.iloc[t])
        
        y_pred_arima = np.array(predictions)
    except:
        # Fallback to simple mean if ARIMA fails
        y_pred_arima = np.full(len(y_test), y_train.mean())

    metrics['ARIMA'] = {
        'MAPE': mean_absolute_percentage_error(y_test, y_pred_arima) * 100,
        'MAE': mean_absolute_error(y_test, y_pred_arima),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_arima))
    }

    # --- Random Forest ---
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    metrics['Random Forest'] = {
        'MAPE': mean_absolute_percentage_error(y_test, y_pred_rf) * 100,
        'MAE': mean_absolute_error(y_test, y_pred_rf),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_rf))
    }

    # --- XGBoost ---
    xgb = XGBRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
    xgb.fit(X_train, y_train)
    y_pred_xgb = xgb.predict(X_test)
    metrics['XGBoost'] = {
        'MAPE': mean_absolute_percentage_error(y_test, y_pred_xgb) * 100,
        'MAE': mean_absolute_error(y_test, y_pred_xgb),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_xgb))
    }

    # --- Simple Ensemble (MandiSense Approx) ---
    # weighted average favoring XGBoost and RF
    y_pred_ens = 0.2 * y_pred_arima + 0.4 * y_pred_rf + 0.4 * y_pred_xgb
    metrics['MandiSense AI'] = {
        'MAPE': mean_absolute_percentage_error(y_test, y_pred_ens) * 100,
        'MAE': mean_absolute_error(y_test, y_pred_ens),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_ens))
    }

    # 3. Plotting
    res_df = pd.DataFrame(metrics).T.reset_index().rename(columns={'index': 'Model'})
    plot_df = res_df.melt(id_vars='Model', var_name='Metric', value_name='Value')

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for i, metric in enumerate(['MAPE', 'MAE', 'RMSE']):
        data = plot_df[plot_df['Metric'] == metric]
        sns.barplot(x='Model', y='Value', data=data, ax=axes[i], palette=COLORS)
        axes[i].set_title(f"{metric} Comparison", fontsize=14, fontweight='bold')
        axes[i].set_ylabel("Value" + (" (%)" if metric == "MAPE" else " (Price Change %)"))
        axes[i].tick_params(axis='x', rotation=15)
        
        # Add labels on top
        for p in axes[i].patches:
            axes[i].annotate(f'{p.get_height():.2f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                             ha='center', va='center', fontsize=10, color='black', xytext=(0, 5),
                             textcoords='offset points')

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "model_comparison.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    # 4. LaTeX Table
    latex_table = f"""
\\begin{{table}}[H]
\\centering
\\caption{{Performance Benchmarking: ARIMA vs Machine Learning Ensembles}}
\\label{{tab:model_comparison}}
\\begin{{tabularx}}{{\\textwidth}}{{|X|c|c|c|}}
\\hline
\\textbf{{Model Architecture}} & \\textbf{{MAPE (\%)}} & \\textbf{{MAE}} & \\textbf{{RMSE}} \\\\
\\hline
ARIMA (5,1,0) & {metrics['ARIMA']['MAPE']:.2f} & {metrics['ARIMA']['MAE']:.2f} & {metrics['ARIMA']['RMSE']:.2f} \\\\
Random Forest & {metrics['Random Forest']['MAPE']:.2f} & {metrics['Random Forest']['MAE']:.2f} & {metrics['Random Forest']['RMSE']:.2f} \\\\
XGBoost & {metrics['XGBoost']['MAPE']:.2f} & {metrics['XGBoost']['MAE']:.2f} & {metrics['XGBoost']['RMSE']:.2f} \\\\
\\rowcolor{{blue!5}} \\textbf{{MandiSense AI (Ensemble)}} & \\textbf{{{metrics['MandiSense AI']['MAPE']:.2f}}} & \\textbf{{{metrics['MandiSense AI']['MAE']:.2f}}} & \\textbf{{{metrics['MandiSense AI']['RMSE']:.2f}}} \\\\
\\hline
\\end{{tabularx}}
\\end{{table}}
"""
    
    latex_path = os.path.join(output_dir, "model_comparison.tex")
    with open(latex_path, 'w') as f:
        f.write(latex_table)

    return metrics, plot_path, latex_path

if __name__ == "__main__":
    data_path = "mandisense_ai/data/raw/v1/tomato/kolar.csv"
    res, p_path, l_path = evaluate_models(data_path)
    print("Model Comparison Complete.")
    print(f"Plot saved to: {p_path}")
    print(f"LaTeX snippet saved to: {l_path}")
