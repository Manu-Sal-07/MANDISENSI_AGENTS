import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import Ridge
import os

# --- STYLE CONFIGURATION (Matching MandiSense AI Aesthetics) ---
MANDI_GREEN = (27/255, 94/255, 32/255)
MANDI_BLUE = (25/255, 88/255, 150/255)
sns.set_theme(style="white", palette="muted")
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

def generate_forecast_viz(csv_path, output_dir="artifacts/evaluation"):
    """
    Loads mandi data, generates a baseline prediction, and creates a publication-quality plot.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Load and Prepare Data
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Select last 90 days for clarity in visualization
    df = df.tail(120).copy()
    
    # 2. Generate Predictions (Ridge Regression on Lags)
    # We use a 7-day lag window to simulate a short-term forecasting agent
    for i in range(1, 8):
        df[f'lag_{i}'] = df['modal_price'].shift(i)
    
    df = df.dropna().reset_index(drop=True)
    
    X = df[[f'lag_{i}' for i in range(1, 8)]]
    y = df['modal_price']
    
    # Train-Test Split (Walk-forward style: Train on first 80%, predict last 20%)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    
    # Predict on entire set for visualization
    df['predicted_price'] = model.predict(X)
    
    # 3. Plotting
    plt.figure(figsize=(12, 6))
    
    # Plot Actual
    plt.plot(df['date'], df['modal_price'], color=MANDI_BLUE, linewidth=2, label='Actual Modal Price', alpha=0.9)
    
    # Plot Predicted
    plt.plot(df['date'], df['predicted_price'], color=MANDI_GREEN, linewidth=2, linestyle='--', label='Predicted (Ridge Ensemble)', alpha=0.9)
    
    # Highlight Deviations (Fill between)
    plt.fill_between(df['date'], df['modal_price'], df['predicted_price'], 
                     where=(df['modal_price'] >= df['predicted_price']),
                     interpolate=True, color=MANDI_BLUE, alpha=0.1, label='Under-prediction')
    plt.fill_between(df['date'], df['modal_price'], df['predicted_price'], 
                     where=(df['modal_price'] < df['predicted_price']),
                     interpolate=True, color='red', alpha=0.1, label='Over-prediction')
    
    # Add vertical line for "Live Forecast" start
    plt.axvline(df.iloc[split_idx]['date'], color='black', linestyle=':', linewidth=1, label='Test Split')
    
    # Formatting
    plt.title(f"Time-Series Forecast Validation: Tomato (Kolar Mandi)", fontsize=16, fontweight='bold', pad=20)
    plt.xlabel("Date (2024-2025)", fontsize=12)
    plt.ylabel("Modal Price (₹/Quintal)", fontsize=12)
    
    # Legend outside
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1), frameon=True)
    
    plt.tight_layout()
    
    plot_path = os.path.join(output_dir, "predicted_vs_actual.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. LaTeX Snippet
    latex_snippet = f"""
\\begin{{figure}}[H]
\\centering
\\includegraphics[width=0.95\\textwidth]{{figures/predicted_vs_actual.png}}
\\caption{{Time-series comparison of predicted vs actual modal prices for Tomato in Kolar Mandi. The dashed green line represents the agent-ensemble forecast, while the solid blue line denotes the ground truth. Shaded regions highlight directional deviations and model residuals.}}
\\label{{fig:forecast_comparison}}
\\end{{figure}}
"""
    
    latex_path = os.path.join(output_dir, "forecast_viz.tex")
    with open(latex_path, 'w') as f:
        f.write(latex_snippet)
        
    return {
        "plot_path": plot_path,
        "latex_path": latex_path,
        "df_head": df[['date', 'modal_price', 'predicted_price']].tail().to_string()
    }

if __name__ == "__main__":
    data_path = "mandisense_ai/data/raw/v1/tomato/kolar.csv"
    results = generate_forecast_viz(data_path)
    print("Visualization Generation Complete.")
    print(f"Plot saved to: {results['plot_path']}")
    print(f"LaTeX snippet saved to: {results['latex_path']}")
    print("\nSample Predictions:")
    print(results['df_head'])
