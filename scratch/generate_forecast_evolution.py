import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- STYLE CONFIGURATION (Academic Infographic Quality) ---
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['text.usetex'] = False

# Create figure
fig, ax = plt.subplots(figsize=(18, 10.5), dpi=300)
ax.set_xlim(0, 18.5)
ax.set_ylim(0, 11)
ax.axis('off')

# Set background to clean white
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# --- TITLE ---
ax.text(9.25, 10.2, "HISTORICAL EVOLUTION OF AGRICULTURAL PRICE FORECASTING METHODOLOGIES", 
        fontsize=16, fontweight='bold', ha='center', va='center', color='#111111')
ax.text(9.25, 9.8, "From Static Statistical Forecasting to Multi-Agent Decision Intelligence (MandiSense AI)", 
        fontsize=11, fontstyle='italic', ha='center', va='center', color='#555555')

# --- TIMELINE STAGES ---
# X-coordinates for the centers of 6 cards
x_centers = [1.5, 4.3, 7.1, 9.9, 12.7, 16.0]
y_center = 5.2

card_w_std = 2.4
card_h_std = 6.4

card_w_mandi = 3.1
card_h_mandi = 7.2

# Stage Data
stages = [
    {
        "title": "STAGE 1\nTraditional Statistical\nForecasting",
        "period": "1990–2010",
        "methods": ["Moving Average", "Exponential Smoothing", "ARIMA", "SARIMA"],
        "strengths": ["Interpretable", "Low computational cost"],
        "limits": ["Assumes stationarity", "Weak shock handling", "Limited nonlinear modeling"],
        "bg": "#F7F8FA", "border": "#7F8C8D", "text_color": "#2C3E50", "accent": "#95A5A6"
    },
    {
        "title": "STAGE 2\nMachine Learning\nForecasting",
        "period": "2010–2018",
        "methods": ["Random Forest", "Support Vector Regression", "Gradient Boosting", "XGBoost"],
        "strengths": ["Nonlinear learning", "Feature interactions"],
        "limits": ["Static learning", "Limited temporal awareness"],
        "bg": "#F4F9F4", "border": "#27AE60", "text_color": "#1E4620", "accent": "#2ECC71"
    },
    {
        "title": "STAGE 3\nDeep Learning\nForecasting",
        "period": "2018–2022",
        "methods": ["LSTM", "GRU", "CNN-LSTM", "Transformer Models"],
        "strengths": ["Long-term dependencies", "Complex temporal learning"],
        "limits": ["Black-box behavior", "Low interpretability", "Data intensive"],
        "bg": "#F4F7FB", "border": "#2980B9", "text_color": "#1B4F72", "accent": "#3498DB"
    },
    {
        "title": "STAGE 4\nHybrid & Ensemble\nForecasting",
        "period": "2022–2024",
        "methods": ["Hybrid ARIMA-LSTM", "Ensemble Learning", "Stacking", "Meta-Learning"],
        "strengths": ["Better robustness", "Improved accuracy"],
        "limits": ["Static weighting", "Limited regime awareness", "Limited explainability"],
        "bg": "#FAF5FC", "border": "#8E44AD", "text_color": "#4A235A", "accent": "#9B59B6"
    },
    {
        "title": "STAGE 5\nIntelligent Market\nAnalytics",
        "period": "2024–2025",
        "methods": ["SHAP / LIME (XAI)", "GARCH Volatility", "HMM Regime Detection", "Granger Causality / VAR"],
        "strengths": ["Explainability", "Volatility awareness", "Cross-commodity linkages"],
        "limits": ["Fragmented intelligence", "No unified reasoning", "No adaptive decisions"],
        "bg": "#FFF9F2", "border": "#D35400", "text_color": "#5E2F0D", "accent": "#E67E22"
    },
    {
        "title": "MANDISENSE AI\nMulti-Agent Decision\nIntelligence",
        "period": "State-of-the-Art (Thesis Proposed)",
        "methods": [
            "• Seasonality & Arrival Agents",
            "• Volatility & HMM Regime Layer",
            "• Cross-Commodity VAR Engine",
            "• Adaptive Meta-Ensemble Layer",
            "• LLM Cognitive Decision Layer"
        ],
        "strengths": [
            "Multi-agent reasoning",
            "Adaptive ensemble weighting",
            "Regime-sensitive dynamics",
            "Explainable trading decisions"
        ],
        "limits": [
            "Actionable Directives:",
            "  BUY / SELL / HOLD / WAIT"
        ],
        "bg": "#F2F6FC", "border": "#1F4E79", "text_color": "#0B2545", "accent": "#D4AF37" # Gold Accent
    }
]

# Plot Cards
for i, s in enumerate(stages):
    is_mandi = (i == 5)
    w = card_w_mandi if is_mandi else card_w_std
    h = card_h_mandi if is_mandi else card_h_std
    x = x_centers[i] - w/2.0
    y = y_center - h/2.0
    
    # Draw Background Card
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                  facecolor=s["bg"], edgecolor=s["border"], 
                                  linewidth=2.5 if is_mandi else 1.5, zorder=2)
    ax.add_patch(rect)
    
    # Top Accent Bar
    accent_bar = patches.FancyBboxPatch((x, y + h - 0.5), w, 0.5, boxstyle="round,pad=0.1", 
                                        facecolor=s["border"], edgecolor="none", zorder=3)
    ax.add_patch(accent_bar)
    
    # Title Text
    ax.text(x_centers[i], y + h - 0.25, s["title"], fontsize=11 if is_mandi else 9.5, 
            fontweight='bold', color='white', ha='center', va='center', zorder=4)
    
    # Period Text
    ax.text(x_centers[i], y + h - 0.8, s["period"], fontsize=9, 
            fontweight='bold', color=s["border"], ha='center', va='center', zorder=4)
    
    # Divider Line
    ax.plot([x + 0.15, x + w - 0.15], [y + h - 1.0, y + h - 1.0], color='#d0d0d0', linewidth=0.8, zorder=4)
    
    # Methods Block
    ax.text(x + 0.15, y + h - 1.2, "Core Framework / Methods:", fontsize=8, fontweight='bold', color='#444444', zorder=4)
    y_curr = y + h - 1.45
    for m in s["methods"]:
        text_m = m if is_mandi else f"• {m}"
        ax.text(x + 0.15, y_curr, text_m, fontsize=8 if is_mandi else 7.5, color=s["text_color"], zorder=4)
        y_curr -= 0.23 if is_mandi else 0.2
        
    # Divider Line 2
    ax.plot([x + 0.15, x + w - 0.15], [y_curr - 0.05, y_curr - 0.05], color='#d0d0d0', linewidth=0.8, zorder=4)
    y_curr -= 0.25
    
    # Strengths Block
    ax.text(x + 0.15, y_curr, "Key Advantages:" if not is_mandi else "Key Innovations:", fontsize=8, fontweight='bold', color='#444444', zorder=4)
    y_curr -= 0.22
    for st in s["strengths"]:
        ax.text(x + 0.15, y_curr, f"✓ {st}", fontsize=7.5, color="#1E8449", zorder=4)
        y_curr -= 0.2
        
    # Divider Line 3
    ax.plot([x + 0.15, x + w - 0.15], [y_curr - 0.05, y_curr - 0.05], color='#d0d0d0', linewidth=0.8, zorder=4)
    y_curr -= 0.25
    
    # Limitations Block
    limit_label = "Unresolved Gaps:" if not is_mandi else "Decision Engine:"
    ax.text(x + 0.15, y_curr, limit_label, fontsize=8, fontweight='bold', color='#444444', zorder=4)
    y_curr -= 0.22
    for li in s["limits"]:
        pfx = "✗ " if not is_mandi else ""
        color_l = "#C0392B" if not is_mandi else "#1F4E79"
        ax.text(x + 0.15, y_curr, f"{pfx}{li}", fontsize=7.5, color=color_l, zorder=4)
        y_curr -= 0.2

# --- DRAW DIRECTIONAL TIMELINE ARROWS ---
for i in range(5):
    # Draw arrow from card i right boundary to card i+1 left boundary
    x1 = x_centers[i] + card_w_std/2.0 + 0.08
    x2 = x_centers[i+1] - (card_w_mandi/2.0 if i == 4 else card_w_std/2.0) - 0.08
    y = y_center
    
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(facecolor='#555555', shrink=0.05, width=1.5, headwidth=6, headlength=6, edgecolor='none'), zorder=5)

# --- BOTTOM INSIGHT BAR ---
# Draw box
bottom_rect = patches.FancyBboxPatch((0.5, 0.7), 17.5, 0.7, boxstyle="round,pad=0.1", 
                                     facecolor="#1F4E79", edgecolor="none", zorder=1)
ax.add_patch(bottom_rect)

# Text inside Bottom Insight Bar
ax.text(9.25, 1.05, "METHODOLOGICAL EVOLUTION DYNAMICS:", 
        fontsize=9, fontweight='bold', color='#D4AF37', ha='center', va='center', zorder=4)

ax.text(9.25, 0.8, 
        "Forecasting Accuracy  ⟶  Operational Robustness  ⟶  Subsystem Explainability  ⟶  Volatility Awareness  ⟶  Cross-Commodity Intelligence  ⟶  Decision Intelligence", 
        fontsize=10.5, fontweight='bold', color='white', ha='center', va='center', zorder=4)

# Save Outputs
imag_dir = "d:\\BMS COLL\\PROJECT\\MS-AI\\imag"
plt.tight_layout()
plt.savefig(os.path.join(imag_dir, 'forecast_evolution.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'forecast_evolution.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'forecast_evolution.svg'), bbox_inches='tight')
plt.close()

print("All evolution timeline infographics generated successfully.")
