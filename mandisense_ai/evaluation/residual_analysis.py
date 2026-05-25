import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os

# --- STYLE CONFIGURATION (Matching MandiSense AI Aesthetics) ---
MANDI_GREEN = (27/255, 94/255, 32/255)
MANDI_BLUE = (25/255, 88/255, 150/255)
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'serif'

def analyze_prediction_errors(df, output_dir="artifacts/evaluation"):
    """
    Computes residuals, plots distribution, and generates statistical summary.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Compute Residuals
    df['residual'] = df['actual_price'] - df['predicted_price']
    
    residuals = df['residual']
    mean_error = residuals.mean()
    std_error = residuals.std()
    rmse = np.sqrt((residuals**2).mean())
    mae = residuals.abs().mean()
    
    # 2. Plotting
    plt.figure(figsize=(10, 6))
    
    # Histogram + KDE
    sns.histplot(residuals, kde=True, color=MANDI_BLUE, bins=30, alpha=0.6, edgecolor='white', label='Residuals')
    
    # Add vertical line for mean
    plt.axvline(mean_error, color='red', linestyle='--', linewidth=1.5, label=f'Mean Error: {mean_error:.4f}')
    
    # Formatting
    plt.title("Distribution of Prediction Residuals ($y - \\hat{y}$)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Residual Value (Price Change %)", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.legend()
    
    plot_path = os.path.join(output_dir, "residual_distribution.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Statistical Summary (LaTeX Table Snippet)
    latex_table = f"""
\\begin{{table}}[H]
\\centering
\\caption{{Statistical Summary of Prediction Residuals}}
\\label{{tab:residual_stats}}
\\begin{{tabularx}}{{0.6\\textwidth}}{{|X|c|}}
\\hline
\\textbf{{Metric}} & \\textbf{{Value}} \\\\
\\hline
Mean Error (Bias) & {mean_error:.4f} \\\\
Standard Deviation & {std_error:.4f} \\\\
Mean Absolute Error (MAE) & {mae:.4f} \\\\
Root Mean Square Error (RMSE) & {rmse:.4f} \\\\
\\hline
\\end{{tabularx}}
\\end{{table}}
"""
    
    latex_path = os.path.join(output_dir, "residual_stats.tex")
    with open(latex_path, 'w') as f:
        f.write(latex_table)
        
    return {
        "mean_error": mean_error,
        "std_error": std_error,
        "mae": mae,
        "rmse": rmse,
        "plot_path": plot_path,
        "latex_path": latex_path
    }

if __name__ == "__main__":
    # Generating Synthetic Evaluation Data for Demonstration
    # This simulates 1000 days of backtest results
    np.random.seed(42)
    actuals = np.random.normal(0, 5, 1000)  # Random price changes
    noise = np.random.normal(0, 1.5, 1000)  # Model errors (Centered around 0)
    preds = actuals - noise # predicted = actual - residual => residual = actual - predicted
    
    test_df = pd.DataFrame({
        'actual_price': actuals,
        'predicted_price': preds
    })
    
    results = analyze_prediction_errors(test_df)
    
    print("Residual Analysis Complete.")
    print(f"Mean Error: {results['mean_error']:.4f}")
    print(f"Std Deviation: {results['std_error']:.4f}")
    print(f"Plot saved to: {results['plot_path']}")
    print(f"LaTeX snippet saved to: {results['latex_path']}")
