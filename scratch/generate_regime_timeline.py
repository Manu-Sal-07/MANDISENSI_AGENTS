import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Append workspace directory to path
sys.path.append('.')

from mandisense_ai.ensemble.regime.garch_estimator import GARCHVolatilityEstimator
from mandisense_ai.ensemble.regime.hmm_classifier import HMMRegimeClassifier

# --- STYLE CONFIGURATION (Academic Publication Quality) ---
plt.rcParams['font.family'] = 'serif'
plt.rcParams['text.usetex'] = False
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['xtick.color'] = '#333333'
plt.rcParams['ytick.color'] = '#333333'

# Color coding for states (subtle transparent bands)
COLOR_STABLE = '#2CA02C'      # Green
COLOR_MEDIUM = '#1F77B4'      # Blue
COLOR_HIGH = '#FF7F0E'        # Orange
COLOR_CRISIS = '#D62728'      # Red

REGIME_NAMES = {1: "Stable", 2: "Medium Volatility", 3: "High Volatility", 4: "Crisis"}


# --- LOAD DATA ---
data_path = 'mandisense_ai/data/raw/v1/tomato/kolar.csv'
df = pd.read_csv(data_path)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# Prepare returns and inputs
df = df.rename(columns={'arrivals': 'arrivals_tonnes'})
df['returns'] = df['modal_price'].pct_change().fillna(0)

print(f"Loaded {len(df)} historical observations.")

# --- FIT GARCH AND ESTIMATE VOLATILITY ---
print("Estimating EGARCH(1,1) conditional volatility...")
garch = GARCHVolatilityEstimator(df['returns'])
garch.fit()
cond_vol = garch.get_conditional_variance()
df_model = df.iloc[-len(cond_vol):].copy()
df_model['garch_volatility'] = cond_vol.values

# Calculate additional HMM features
df_model['realized_volatility'] = df_model['returns'].rolling(7).std().fillna(0)
df_model['momentum'] = df_model['returns'].rolling(7).sum().fillna(0)
mean_a = df_model['arrivals_tonnes'].mean()
std_a = df_model['arrivals_tonnes'].std()
df_model['volume_stress'] = ((df_model['arrivals_tonnes'] - mean_a) / (std_a + 1e-9)).fillna(0)

# --- FIT HMM AND PREDICT REGIMES ---
print("Fitting Gaussian Hidden Markov Model...")
hmm = HMMRegimeClassifier(n_states=4)
features = hmm.prepare_features(df_model)
hmm.fit(features)
states = hmm.predict_state_sequence(features)
df_model['regime'] = states

# Transition probabilities
state_stats = hmm.get_state_statistics()

# --- DETECT VOLATILITY ALERTS ---
# Calculate thresholds based on rolling volatility
rolling_vol_mean = df_model['garch_volatility'].mean()
rolling_vol_std = df_model['garch_volatility'].std()

threshold_2sigma = rolling_vol_mean + 2.0 * rolling_vol_std
threshold_3sigma = rolling_vol_mean + 3.0 * rolling_vol_std

df_model['alert'] = 0  # 0: normal, 1: 2sigma warning, 2: 3sigma critical
df_model.loc[df_model['garch_volatility'] >= threshold_2sigma, 'alert'] = 1
df_model.loc[df_model['garch_volatility'] >= threshold_3sigma, 'alert'] = 2

n_warning_alerts = (df_model['alert'] == 1).sum()
n_critical_alerts = (df_model['alert'] == 2).sum()

print(f"Detected {n_warning_alerts} warning alerts (2-sigma) and {n_critical_alerts} critical alerts (3-sigma).")

# --- DETECT TRANSITIONS ---
df_model['regime_shift'] = df_model['regime'].diff().fillna(0)
transitions = df_model[df_model['regime_shift'] != 0].copy()

# Keep a subset of major transitions for clean visualization annotations
major_transitions = []
prev_state = df_model.iloc[0]['regime']
for idx, row in df_model.iterrows():
    curr_state = row['regime']
    if curr_state != prev_state:
        major_transitions.append({
            "date": row['date'],
            "from": prev_state,
            "to": curr_state,
            "price": row['modal_price']
        })
        prev_state = curr_state

# --- PLOT THE THREE-LAYER TIMELINE ---
# Filter data for a focused evaluation timeline (e.g., last 350 trading days for high density readability)
df_plot = df_model.tail(350).reset_index(drop=True)

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 8.5), dpi=300, sharex=True,
                                     gridspec_kw={'height_ratios': [4, 3, 1.2]})

# --- LAYER 1: PRICE SERIES WITH REGIME BACKGROUND BANDS ---
ax1.plot(df_plot['date'], df_plot['modal_price'], color='#333333', linewidth=1.5, label='Modal Price (Rs/Quintal)')
ax1.set_ylabel("Commodity Price (Rs/Qtl)", fontsize=11, fontweight='bold', labelpad=8)
ax1.set_title("Figure 5.4: Volatility and Regime Detection Timeline", fontsize=13, fontweight='bold', pad=15)

# Background shading according to regime
for i in range(len(df_plot) - 1):
    d1 = df_plot.loc[i, 'date']
    d2 = df_plot.loc[i+1, 'date']
    reg = df_plot.loc[i, 'regime']
    
    if reg == 1:
        color = COLOR_STABLE
    elif reg == 2:
        color = COLOR_MEDIUM
    elif reg == 3:
        color = COLOR_HIGH
    else:
        color = COLOR_CRISIS
        
    ax1.axvspan(d1, d2, facecolor=color, alpha=0.15)

# Add color legend manually for background bands
from matplotlib.patches import Patch
regime_patches = [
    Patch(facecolor=COLOR_STABLE, alpha=0.25, label='Stable Regime'),
    Patch(facecolor=COLOR_MEDIUM, alpha=0.25, label='Medium Volatility'),
    Patch(facecolor=COLOR_HIGH, alpha=0.25, label='High Volatility'),
    Patch(facecolor=COLOR_CRISIS, alpha=0.25, label='Crisis / Shock')
]
ax1.legend(handles=regime_patches + [plt.Line2D([0], [0], color='#333333', linewidth=1.5, label='Actual Price')], 
           loc='upper left', fontsize=9, frameon=True, facecolor='white', edgecolor='#e0e0e0')

# --- LAYER 2: VOLATILITY OVERLAY & ALERTS ---
ax2.plot(df_plot['date'], df_plot['garch_volatility'] * 100.0, color=COLOR_MEDIUM, linewidth=1.2, label='GARCH Conditional Volatility')
# Add a rolling realized volatility
ax2.plot(df_plot['date'], df_plot['realized_volatility'] * 100.0, color='#888888', linestyle='--', linewidth=0.8, label='7-Day Realized Volatility')

# Threshold lines
ax2.axhline(threshold_2sigma * 100.0, color='#E6A23C', linestyle=':', linewidth=1.0, label='$2\\sigma$ Warning Threshold')
ax2.axhline(threshold_3sigma * 100.0, color='#F56C6C', linestyle='-.', linewidth=1.0, label='$3\\sigma$ Critical Threshold')

# Mark alerts
warnings = df_plot[df_plot['alert'] == 1]
criticals = df_plot[df_plot['alert'] == 2]

ax2.scatter(warnings['date'], warnings['garch_volatility'] * 100.0, color='#E6A23C', marker='^', s=45, zorder=5, label='Warning Alert ($2\\sigma$)')
ax2.scatter(criticals['date'], criticals['garch_volatility'] * 100.0, color='#F56C6C', marker='v', s=45, zorder=5, label='Critical Alert ($3\\sigma$)')

ax2.set_ylabel("Conditional Volatility (%)", fontsize=11, fontweight='bold', labelpad=8)
ax2.legend(loc='upper right', fontsize=8, frameon=True, facecolor='white', edgecolor='#e0e0e0')
ax2.grid(True, linestyle=':', alpha=0.4)

# --- LAYER 3: REGIME SEQUENCING BAND ---
# Create a categorical timeline
regime_seq = df_plot['regime'].values.reshape(1, -1)
ax3.imshow(regime_seq, aspect='auto', cmap=plt.cm.get_cmap('RdYlGn_r', 4), 
           extent=[mdates.date2num(df_plot['date'].iloc[0]), mdates.date2num(df_plot['date'].iloc[-1]), 0, 1],
           alpha=0.8)
ax3.set_yticks([])
ax3.set_ylabel("Regime State", fontsize=11, fontweight='bold', labelpad=8)

# Format bottom X-axis
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=0)

# Annotate some major transition lines
major_plot_transitions = [t for t in major_transitions if t['date'] >= df_plot['date'].iloc[0]]
for i, t in enumerate(major_plot_transitions[:5]):
    # Draw vertical dashed line across top two panels
    ax1.axvline(t['date'], color='#666666', linestyle='--', linewidth=0.8, alpha=0.7)
    ax2.axvline(t['date'], color='#666666', linestyle='--', linewidth=0.8, alpha=0.7)
    
    # Label the transition on the price chart
    label = f"S{t['from']} $\\rightarrow$ S{t['to']}"
    ax1.text(t['date'], t['price'] + (i % 2 * 300 - 150), label, rotation=90, 
             fontsize=8, fontweight='bold', color='#444444', ha='right', va='bottom')

# Adjust layout
plt.tight_layout()

# Save figures
imag_dir = "d:\\BMS COLL\\PROJECT\\MS-AI\\imag"
if not os.path.exists(imag_dir):
    os.makedirs(imag_dir)

plt.savefig(os.path.join(imag_dir, 'figure_5_4_regime_timeline.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'regime_timeline.png'), dpi=300, bbox_inches='tight') # For LaTeX mapping
plt.savefig(os.path.join(imag_dir, 'figure_5_4_regime_timeline.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'figure_5_4_regime_timeline.svg'), bbox_inches='tight')
plt.close()

print("Timeline figures generated successfully.")

# --- STATISTICS COMPUTATION ---
stats = []
for r in [1, 2, 3, 4]:
    r_data = df_model[df_model['regime'] == r]
    avg_vol = r_data['garch_volatility'].mean() * 100.0
    max_vol = r_data['garch_volatility'].max() * 100.0
    stats.append({
        "Regime": r,
        "Name": REGIME_NAMES[r],
        "Count": len(r_data),
        "Avg_Vol": avg_vol,
        "Max_Vol": max_vol
    })

max_vol_overall = df_model['garch_volatility'].max() * 100.0
n_total_observations = len(df_model)

# --- GENERATE LATEX STATISTICS TABLE ---
latex_table = f"""% Generated Regime Performance Statistics Table
\\begin{{table}}[htbp]
\\centering
\\caption{{Empirical Analysis of Hidden Markov Model Regimes and GARCH Volatility Alerts}}
\\label{{tab:regime_timeline_stats}}
\\begin{{tabularx}}{{\\textwidth}}{{|c|X|c|c|c|}}
\\hline
\\rowcolor{{gray!10}}
\\textbf{{State}} & \\textbf{{Market Regime Classification}} & \\textbf{{Trading Days ($N$)}} & \\textbf{{Mean GARCH Volatility (\\%)}} & \\textbf{{Peak Conditional Volatility (\\%)}} \\\\
\\hline
1 & {stats[0]['Name']} & {stats[0]['Count']} & {stats[0]['Avg_Vol']:.3f}\\% & {stats[0]['Max_Vol']:.3f}\\% \\\\
\\hline
2 & {stats[1]['Name']} & {stats[1]['Count']} & {stats[1]['Avg_Vol']:.3f}\\% & {stats[1]['Max_Vol']:.3f}\\% \\\\
\\hline
3 & {stats[2]['Name']} & {stats[2]['Count']} & {stats[2]['Avg_Vol']:.3f}\\% & {stats[2]['Max_Vol']:.3f}\\% \\\\
\\hline
4 & {stats[3]['Name']} & {stats[3]['Count']} & {stats[3]['Avg_Vol']:.3f}\\% & {stats[3]['Max_Vol']:.3f}\\% \\\\
\\hline
\\multicolumn{{2}}{{|l|}}{{\\textbf{{Total Historical Trading Horizon}}}} & \\multicolumn{{3}}{{c|}}{{{n_total_observations} Days}} \\\\
\\hline
\\multicolumn{{2}}{{|l|}}{{\\textbf{{Volatility Alert Trigger Summary}}}} & \\multicolumn{{3}}{{c|}}{{{n_warning_alerts} Warning Alerts ($2\\sigma$), {n_critical_alerts} Critical Alerts ($3\\sigma$)}} \\\\
\\hline
\\end{{tabularx}}
\\end{{table}}
"""

artifacts_dir = 'd:\\BMS COLL\\PROJECT\\MS-AI\\MS-AI\\artifacts\\evaluation'
with open(os.path.join(artifacts_dir, 'regime_timeline_stats.tex'), 'w') as f:
    f.write(latex_table)

print("LaTeX table generated successfully.")
