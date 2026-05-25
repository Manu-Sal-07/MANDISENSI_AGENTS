import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import Ridge
import os

# --- STYLE CONFIGURATION ---
MANDI_GREEN = (27/255, 94/255, 32/255)
MANDI_BLUE = (25/255, 88/255, 150/255)
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'serif'

def analyze_regime_performance(csv_path, output_dir="artifacts/evaluation"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Load and Prepare Data
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # 2. Compute Volatility and Regimes
    # Use 7-day returns for volatility to capture short-term mandi dynamics
    df['returns'] = df['modal_price'].pct_change(periods=7) * 100.0
    df['volatility'] = df['returns'].rolling(window=30).std()
    
    # Define thresholds based on quantiles
    v_low = df['volatility'].quantile(0.33)
    v_high = df['volatility'].quantile(0.66)
    
    def classify_regime(v):
        if pd.isna(v): return np.nan
        if v <= v_low: return 'Stable'
        if v <= v_high: return 'Volatile'
        return 'Shock'
    
    df['regime'] = df['volatility'].apply(classify_regime)
    
    # 3. Simulate Model Predictions (Ridge Ensemble)
    for i in range(1, 8):
        df[f'lag_{i}'] = df['modal_price'].pct_change(periods=1).shift(i) * 100.0
    
    # Target is next 7-day change
    df['target'] = df['modal_price'].pct_change(periods=7).shift(-7) * 100.0
    
    df_clean = df.dropna().copy()
    X = df_clean[[f'lag_{i}' for i in range(1, 8)]]
    y = df_clean['target']
    
    model = Ridge(alpha=1.0)
    model.fit(X, y)
    df_clean['prediction'] = model.predict(X)
    df_clean['abs_error'] = (df_clean['target'] - df_clean['prediction']).abs()
    
    # 4. Aggregate Metrics per Regime
    regime_stats = df_clean.groupby('regime')['abs_error'].agg(['mean', 'std', 'count']).reindex(['Stable', 'Volatile', 'Shock'])
    
    # 5. Plotting
    plt.figure(figsize=(10, 6))
    colors = [MANDI_GREEN, MANDI_BLUE, '#D32F2F'] # Green for stable, Blue for volatile, Red for shock
    
    ax = sns.barplot(x=regime_stats.index, y='mean', data=regime_stats, palette=colors, alpha=0.85)
    
    # Add error bars (standard deviation)
    plt.errorbar(x=range(3), y=regime_stats['mean'], yerr=regime_stats['std']/np.sqrt(regime_stats['count']), 
                 fmt='none', c='black', capsize=5, elinewidth=1.5)
    
    # Formatting
    plt.title("Model Error (MAE) Across Market Regimes", fontsize=15, fontweight='bold', pad=20)
    plt.xlabel("Market Regime (Volatility Level)", fontsize=12)
    plt.ylabel("Mean Absolute Error (%)", fontsize=12)
    
    # Annotate values
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}%', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=11, color='black', xytext=(0, 10),
                    textcoords='offset points', fontweight='bold')

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "regime_performance.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 6. LaTeX Snippet
    latex_table = f"""
\\begin{{table}}[H]
\\centering
\\caption{{Regime-Aware Performance Analysis (MAE by Volatility)}}
\\label{{tab:regime_performance}}
\\begin{{tabularx}}{{0.7\\textwidth}}{{|X|c|c|}}
\\hline
\\textbf{{Market Regime}} & \\textbf{{Volatility Range ($\\sigma$)}} & \\textbf{{Mean Absolute Error (MAE)}} \\\\
\\hline
Stable & $<$ {v_low:.2f} & {regime_stats.loc['Stable', 'mean']:.2f}\\% \\\\
Volatile & {v_low:.2f} -- {v_high:.2f} & {regime_stats.loc['Volatile', 'mean']:.2f}\\% \\\\
Shock & $>$ {v_high:.2f} & {regime_stats.loc['Shock', 'mean']:.2f}\\% \\\\
\\hline
\\end{{tabularx}}
\\end{{table}}
"""
    
    latex_path = os.path.join(output_dir, "regime_performance.tex")
    with open(latex_path, 'w') as f:
        f.write(latex_table)
        
    return regime_stats, plot_path, latex_path

if __name__ == "__main__":
    data_path = "mandisense_ai/data/raw/v1/tomato/kolar.csv"
    stats, p_path, l_path = analyze_regime_performance(data_path)
    print("Regime Analysis Complete.")
    print(f"Plot saved to: {p_path}")
    print(f"LaTeX snippet saved to: {l_path}")
    print("\nRegime Statistics:")
    print(stats)
