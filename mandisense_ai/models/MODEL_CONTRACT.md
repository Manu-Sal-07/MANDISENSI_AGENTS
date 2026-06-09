# 🏗️ MandiSense AI Model Standardization Contract (v1)

This document defines the strict contract for model storage and inference. All agents and commodities MUST adhere to this standard.

---

## 📂 1. Directory Structure

All models are stored under `mandisense_ai/models/`.

```text
/models/
  /seasonality/
    /{commodity}/
      bundle.pkl      <-- Inference Engine
      metadata.json   <-- Provenance & Configuration

  /arrival/
    /{commodity}/
      bundle.pkl      <-- Inference Engine
      metrics.json    <-- Performance & Weights
```

### Constraints:
- No nested mandi-specific folders (e.g., `tomato_kolar` is deprecated in favor of `tomato`).
- One folder per commodity (all lowercase).
- Exactly one `bundle.pkl` per commodity per agent.

---

## 📦 2. Bundle Specification (bundle.pkl)

The `bundle.pkl` is a pickled dictionary that must be self-sufficient for inference.

### 2.1 Seasonality Agent Bundle
```python
{
    "version": "v1",
    "commodity": str,
    "models": { "model_name": object }, # Trained models (e.g., SARIMA, XGB)
    "stl_components": {
        "trend": pd.Series,
        "seasonal": pd.Series,
        "residual": pd.Series
    },
    "feature_config": {
        "lags": list,
        "windows": list,
        "target_col": str
    },
    "scaler": object | None, # sklearn scaler instance
    "trained_at": str (ISO 8601)
}
```

### 2.2 Arrival Agent Bundle
```python
{
    "version": "v1",
    "commodity": str,
    "models": [ object ], # List of ensemble models
    "weights": [ float ], # Normalized ensemble weights
    "feature_config": {
        "feature_names": list,
        "lags": list
    },
    "scaler": object | None,
    "trained_at": str (ISO 8601)
}
```

---

## 📄 3. Metadata & Metrics

### 3.1 seasonality/metadata.json
```json
{
  "commodity": "tomato",
  "trained_on": "2026-05-03",
  "features_used": ["lag1", "lag7", "seasonal_7d"],
  "model_types": ["sarima", "xgboost", "random_forest"],
  "horizons": [3, 7, 30]
}
```

### 3.2 arrival/metrics.json
```json
{
  "commodity": "tomato",
  "cv_mae": 14.2,
  "models_used": ["xgboost", "lightgbm", "lasso"],
  "ensemble_weights": [0.4, 0.4, 0.2]
}
```

---

## 🔄 4. Loading Contract

Inference code must use a unified loading pattern:

```python
def load_bundle(path):
    with open(path, 'rb') as f:
        bundle = pickle.load(f)
    
    assert bundle["version"] == "v1", f"Incompatible version: {bundle['version']}"
    return bundle
```

Legacy formats like `ensemble_summary.json` without a `bundle.pkl` are **strictly rejected**.
