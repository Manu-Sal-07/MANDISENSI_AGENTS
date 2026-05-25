import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- STYLE CONFIGURATION ---
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['text.usetex'] = False

# Create figure
fig, ax = plt.subplots(figsize=(19, 12), dpi=300)
ax.set_xlim(0, 19)
ax.set_ylim(0, 11)
ax.axis('off')

# Set background to clean white
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# --- TITLE ---
ax.text(9.5, 10.4, "TAXONOMY OF AGRICULTURAL TIME-SERIES FORECASTING APPROACHES", 
        fontsize=16, fontweight='bold', ha='center', va='center', color='#111111')
ax.text(9.5, 10.05, "Classification of Modeling Paradigms, Analytical Properties, and the Emergence of Decision Intelligence", 
        fontsize=11, fontstyle='italic', ha='center', va='center', color='#555555')

# --- ROOT NODE ---
root_x = 9.5
root_y = 9.4
root_w = 4.8
root_h = 0.6
root_box = patches.FancyBboxPatch((root_x - root_w/2.0, root_y - root_h/2.0), root_w, root_h, 
                                  boxstyle="round,pad=0.08", facecolor="#1F4E79", edgecolor="none", zorder=3)
ax.add_patch(root_box)
ax.text(root_x, root_y, "Agricultural Price Forecasting Framework", 
        fontsize=12, fontweight='bold', color='white', ha='center', va='center', zorder=4)

# --- LEVEL 1 CATEGORY CARDS ---
# X coordinates of 4 main columns
x_cols = [2.2, 6.0, 9.8, 15.0]
y_lvl1 = 7.2
w_std = 3.2
h_std = 3.2

categories = [
    {
        "title": "1. Statistical Models",
        "sub": ["Moving Average", "Exponential Smoothing", "ARIMA / SARIMA"],
        "props": [
            "Interpretability: High (✓)",
            "Data Requirement: Low (✓)",
            "Adaptability: Low (✗)",
            "Decision Support: None (✗)"
        ],
        "bg": "#F5F7FA", "border": "#7F8C8D", "accent": "#95A5A6", "text": "#2C3E50"
    },
    {
        "title": "2. Machine Learning Models",
        "sub": ["Random Forest / SVR", "Gradient Boosting", "XGBoost / LightGBM"],
        "props": [
            "Interpretability: Medium (~)",
            "Data Requirement: Medium (~)",
            "Adaptability: Medium (~)",
            "Decision Support: None (✗)"
        ],
        "bg": "#F4FDF4", "border": "#27AE60", "accent": "#2ECC71", "text": "#1E4620"
    },
    {
        "title": "3. Deep Learning Models",
        "sub": ["LSTM / GRU Networks", "CNN-LSTM Hybrids", "Temporal Transformers"],
        "props": [
            "Interpretability: Low (✗)",
            "Data Requirement: High (✗)",
            "Adaptability: Low (✗)",
            "Decision Support: None (✗)"
        ],
        "bg": "#F4F7FC", "border": "#2980B9", "accent": "#3498DB", "text": "#1B4F72"
    },
    {
        "title": "4. Intelligent Decision Systems",
        "sub": [
            "Ensemble Fusion Architectures",
            "Explainable AI (XAI) Frameworks",
            "Volatility-Aware Risk Models",
            "Multi-Agent Market Intelligence"
        ],
        "props": [
            "Interpretability: High (✓)",
            "Data Requirement: Medium (~)",
            "Adaptability: High (✓)",
            "Decision Support: Actionable (✓)"
        ],
        "bg": "#FCF9F2", "border": "#D35400", "accent": "#E67E22", "text": "#5E2F0D"
    }
]

# Draw level 1 cards
for i, c in enumerate(categories):
    is_large = (i == 3)
    w = 5.4 if is_large else w_std
    h = h_std
    x = x_cols[i] - w/2.0
    y = y_lvl1 - h/2.0
    
    # Draw Box
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", 
                                  facecolor=c["bg"], edgecolor=c["border"], linewidth=1.5, zorder=2)
    ax.add_patch(rect)
    
    # Top bar
    tbar = patches.FancyBboxPatch((x, y + h - 0.4), w, 0.4, boxstyle="round,pad=0.08", 
                                  facecolor=c["border"], edgecolor="none", zorder=3)
    ax.add_patch(tbar)
    
    # Title
    ax.text(x_cols[i], y + h - 0.2, c["title"], fontsize=10.5, fontweight='bold', color='white', ha='center', va='center', zorder=4)
    
    # Subcategories
    ax.text(x + 0.15, y + h - 0.65, "Subcategories:", fontsize=8.5, fontweight='bold', color='#444444', zorder=4)
    y_curr = y + h - 0.9
    for sb in c["sub"]:
        ax.text(x + 0.15, y_curr, f"• {sb}", fontsize=8, color=c["text"], zorder=4)
        y_curr -= 0.22
        
    # Divider
    ax.plot([x + 0.15, x + w - 0.15], [y_curr, y_curr], color='#d0d0d0', linewidth=0.6, zorder=4)
    y_curr -= 0.25
    
    # Analytical properties
    ax.text(x + 0.15, y_curr, "Analytical Profile:", fontsize=8.5, fontweight='bold', color='#444444', zorder=4)
    y_curr -= 0.22
    for pr in c["props"]:
        # Set color based on ✓ or ✗
        color_p = '#1E8449' if '(✓)' in pr else ('#C0392B' if '(✗)' in pr else '#7F8C8D')
        ax.text(x + 0.15, y_curr, pr, fontsize=7.5, fontweight='bold', color=color_p, zorder=4)
        y_curr -= 0.2

# --- LEVEL 2 BRANCHES (Under Category 4) ---
# Category 4 branches into 4 specialized layers at y = 4.2
y_lvl2 = 4.2
w_branch = 1.25
h_branch = 1.3
x_branches = [12.6, 14.2, 15.8, 17.4]

branches = [
    {
        "title": "Ensemble\nLearning",
        "items": ["Stacking", "Blending", "Meta-Learning"],
        "color": "#8E44AD", "bg": "#F5EEF8"
    },
    {
        "title": "Explainable\nAI (XAI)",
        "items": ["SHAP Analysis", "LIME Explainer", "Rule Engines"],
        "color": "#2980B9", "bg": "#EBF5FB"
    },
    {
        "title": "Volatility\nIntelligence",
        "items": ["GARCH / EGARCH", "Markov States", "Regime HMM"],
        "color": "#16A085", "bg": "#E8F8F5"
    },
    {
        "title": "Market\nIntelligence",
        "items": ["Granger Causality", "VAR Modeling", "Spillover Net"],
        "color": "#27AE60", "bg": "#E8F8F5"
    }
]

for i, br in enumerate(branches):
    x = x_branches[i] - w_branch/2.0
    y = y_lvl2 - h_branch/2.0
    
    rect = patches.FancyBboxPatch((x, y), w_branch, h_branch, boxstyle="round,pad=0.06", 
                                  facecolor=br["bg"], edgecolor=br["color"], linewidth=1.2, zorder=2)
    ax.add_patch(rect)
    
    # Title
    ax.text(x_branches[i], y + h_branch - 0.25, br["title"], fontsize=8.5, fontweight='bold', color=br["color"], ha='center', va='center', zorder=4)
    
    # Items
    y_curr = y + h_branch - 0.55
    for it in br["items"]:
        ax.text(x_branches[i], y_curr, it, fontsize=7.5, color='#444444', ha='center', va='center', zorder=4)
        y_curr -= 0.22

# --- FINAL HIGHLIGHTED TERMINAL NODE (MandiSense AI) ---
mandi_x = 15.0
mandi_y = 1.7
mandi_w = 5.2
mandi_h = 2.0

mandi_rect = patches.FancyBboxPatch((mandi_x - mandi_w/2.0, mandi_y - mandi_h/2.0), mandi_w, mandi_h, 
                                     boxstyle="round,pad=0.08", facecolor="#EBF3F9", edgecolor="#1F4E79", linewidth=2.5, zorder=3)
ax.add_patch(mandi_rect)

# Top Bar
mandi_tbar = patches.FancyBboxPatch((mandi_x - mandi_w/2.0, mandi_y + mandi_h/2.0 - 0.35), mandi_w, 0.35, 
                                     boxstyle="round,pad=0.08", facecolor="#1F4E79", edgecolor="none", zorder=4)
ax.add_patch(mandi_tbar)

# Title
ax.text(mandi_x, mandi_y + mandi_h/2.0 - 0.17, "MANDISENSE AI (PROPOSED ARCHITECTURE)", 
        fontsize=10, fontweight='bold', color='white', ha='center', va='center', zorder=5)

# Details
ax.text(mandi_x - mandi_w/2.0 + 0.15, mandi_y + 0.45, 
        "Unified Multi-Agent Decision Framework\n"
        "• Specialized Agents: Seasonality, Arrival, External Intelligence\n"
        "• Adaptive Blending: Alpha Ridge Meta-Ensemble Fusion\n"
        "• Risk Integration: GARCH-HMM Volatility & VAR Spillovers\n"
        "• Cognitive Delivery: LLM-Driven Advisory & Actionable Signals", 
        fontsize=8, color="#0B2545", ha='left', va='center', zorder=5)

# --- DRAW CONNECTOR LINES (TIMELINE / ARCHITECTURE HIERARCHY) ---
# 1. Root to Level 1
for xc in x_cols:
    ax.plot([root_x, root_x], [root_y - root_h/2.0, root_y - root_h/2.0 - 0.2], color='#555555', linewidth=1.2, zorder=1)
    ax.plot([root_x, xc], [root_y - root_h/2.0 - 0.2, root_y - root_h/2.0 - 0.2], color='#555555', linewidth=1.2, zorder=1)
    ax.annotate('', xy=(xc, y_lvl1 + h_std/2.0), xytext=(xc, root_y - root_h/2.0 - 0.2),
                arrowprops=dict(arrowstyle="->", color='#555555', linewidth=1.2), zorder=1)

# 2. Category 4 to Level 2 Branches
cat4_bottom_x = x_cols[3]
cat4_bottom_y = y_lvl1 - h_std/2.0
for xb in x_branches:
    ax.plot([cat4_bottom_x, cat4_bottom_x], [cat4_bottom_y, cat4_bottom_y - 0.15], color='#D35400', linewidth=1.0, zorder=1)
    ax.plot([cat4_bottom_x, xb], [cat4_bottom_y - 0.15, cat4_bottom_y - 0.15], color='#D35400', linewidth=1.0, zorder=1)
    ax.annotate('', xy=(xb, y_lvl2 + h_branch/2.0), xytext=(xb, cat4_bottom_y - 0.15),
                arrowprops=dict(arrowstyle="->", color='#D35400', linewidth=1.0), zorder=1)

# 3. Level 2 Branches to MandiSense AI Terminal Node
for xb in x_branches:
    branch_bottom_y = y_lvl2 - h_branch/2.0
    ax.annotate('', xy=(xb, mandi_y + mandi_h/2.0), xytext=(xb, branch_bottom_y),
                arrowprops=dict(arrowstyle="->", color='#1F4E79', linewidth=1.2, linestyle='--'), zorder=1)

# --- LEFT SIDE TAXONOMY PROPERTIES LEGEND ---
# Draw box on the left summarizing structural classifications
leg_x = 2.2
leg_y = 1.7
leg_w = 3.2
leg_h = 2.0
leg_rect = patches.FancyBboxPatch((leg_x - leg_w/2.0, leg_y - leg_h/2.0), leg_w, leg_h, 
                                  boxstyle="round,pad=0.08", facecolor="#F8F9FA", edgecolor="#7F8C8D", linewidth=1.2, zorder=2)
ax.add_patch(leg_rect)

ax.text(leg_x, leg_y + leg_h/2.0 - 0.25, "TAXONOMY KEY & METRICS", fontsize=9.5, fontweight='bold', color='#2C3E50', ha='center', va='center', zorder=4)
ax.text(leg_x - leg_w/2.0 + 0.15, leg_y - 0.2,
        "✓ : Highly Optimized / Capable\n"
        "~ : Partially Optimized\n"
        "✗ : Limited / Not Present\n\n"
        "Note: Traditional approaches focus\n"
        "strictly on numerical forecasting,\n"
        "lacking contextual intelligence.", 
        fontsize=8.5, color='#444444', ha='left', va='center', zorder=4)

# --- BOTTOM INSIGHT PANEL ---
bottom_rect = patches.FancyBboxPatch((0.5, 0.4), 18.0, 0.5, boxstyle="round,pad=0.08", 
                                     facecolor="#1F4E79", edgecolor="none", zorder=1)
ax.add_patch(bottom_rect)

ax.text(9.5, 0.45, 
        "CORE TAXONOMICAL INSIGHT: Forecasting methodologies evolve from rigid, prediction-focused mathematical models "
        "toward adaptive, explainable, and decision-oriented multi-agent intelligence systems.", 
        fontsize=10, fontweight='bold', color='white', ha='center', va='center', zorder=4)

# Save Outputs
imag_dir = "d:\\BMS COLL\\PROJECT\\MS-AI\\imag"
plt.tight_layout()
plt.savefig(os.path.join(imag_dir, 'forecasting_taxonomy.png'), dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'forecasting_taxonomy.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(imag_dir, 'forecasting_taxonomy.svg'), bbox_inches='tight')
plt.close()

print("All taxonomy infographics generated successfully.")
