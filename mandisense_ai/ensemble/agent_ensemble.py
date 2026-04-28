"""
AgentEnsemble — Canonical Internal Ensemble Engine for MandiSense AI.

This is the single source of truth for all ensemble logic across BOTH the
SeasonalityAgent and ArrivalVolumeAgent.  Neither agent should re-implement
walk-forward CV, weight calculation, or weighted prediction independently.

Design:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  AgentEnsemble.fit(X, y, regime_flags)                              │
  │    ├── For each model in self.models:                               │
  │    │     ├── TimeSeriesSplit(n_splits) walk-forward CV              │
  │    │     ├── Collect per-fold MAPE                                  │
  │    │     └── Store: fold predictions, fold errors                   │
  │    ├── Rank models by avg MAPE                                      │
  │    ├── Compute weights: w_i = (1/MAPE_i) / Σ(1/MAPE_j)            │
  │    └── Refit all top-N models on FULL training data                 │
  │                                                                      │
  │  AgentEnsemble.predict(X)                                           │
  │    ├── Call each fitted model's predict(X)                          │
  │    ├── Store per-model predictions in self.last_predictions         │
  │    └── Return weighted sum                                          │
  │                                                                      │
  │  AgentEnsemble.get_ensemble_log()                                   │
  │    └── Returns dict: weights, errors, model predictions, metadata   │
  └──────────────────────────────────────────────────────────────────────┘

Logging strategy:
  - After fit():   self.weights, self.errors, self.cv_fold_errors populated
  - After predict(): self.last_predictions populated
  - get_ensemble_log() serialises everything into one audit dict that agents
    can dump directly into AgentOutput.metadata

Thread safety: This class is NOT thread-safe by design.  Each agent call
creates a fresh AgentEnsemble instance, so no shared state exists.
"""

from __future__ import annotations

import copy
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

from utils.logger import get_logger

logger = get_logger(__name__)


class AgentEnsemble:
    """
    Internal ensemble engine.  Accepts any dict of {name: model_instance}
    where every model implements `fit(X, y)` and `predict(X) -> np.ndarray`.

    Parameters
    ----------
    models : dict
        {model_name: unfitted_model_instance}
        Models must follow BaseSeasonalityModel or BaseArrivalModel interface.
    n_splits : int
        Number of TimeSeriesSplit folds for walk-forward CV.
    top_n : int
        Maximum number of models to keep in the final ensemble.
        Set to len(models) to keep all.
    min_weight_threshold : float
        Models whose normalised weight falls below this threshold after
        weight calculation are dropped from the ensemble silently.
        Default 0.01 (1%) prevents near-zero-weight models from adding noise.
    """

    # ------------------------------------------------------------------ #
    #  Public state (readable after fit / predict)                        #
    # ------------------------------------------------------------------ #
    weights: Dict[str, float]            # normalised inverse-MAPE weights
    errors: Dict[str, float]             # avg MAPE per model (from CV)
    cv_fold_errors: Dict[str, List[float]]  # per-fold MAPE per model
    last_predictions: Dict[str, float]   # {model_name: scalar pred} at last predict() call
    last_ensemble_prediction: Optional[float]  # scalar ensemble output at last predict()

    # ------------------------------------------------------------------ #
    def __init__(
        self,
        models: Dict[str, Any],
        n_splits: int = 5,
        top_n: int = 9,
        min_weight_threshold: float = 0.01,
    ):
        if not models:
            raise ValueError("AgentEnsemble requires at least one model.")

        # Deep-copy at construction so callers can reuse their registry dict
        self.models: Dict[str, Any] = {
            name: copy.deepcopy(m) for name, m in models.items()
        }
        self.n_splits              = n_splits
        self.top_n                 = min(top_n, len(models))
        self.min_weight_threshold  = min_weight_threshold

        # State initialised at fit()
        self.weights              = {}
        self.errors               = {}
        self.cv_fold_errors       = {}
        self._fitted_models: Dict[str, Any] = {}
        self._is_fitted           = False

        # State initialised at predict()
        self.last_predictions          = {}
        self.last_ensemble_prediction  = None

        # Audit trail: captures timing and metadata per fit() call
        self._fit_metadata: Dict[str, Any] = {}

    # ================================================================== #
    #  Step 2 — Training Phase                                            #
    # ================================================================== #
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        regime_flags: Optional[pd.Series] = None,
    ) -> "AgentEnsemble":
        """
        Train all models via walk-forward CV and compute ensemble weights.

        Args:
            X:            Feature DataFrame (NaN-free is preferred; fillna(0) applied internally).
            y:            Target Series.
            regime_flags: Optional binary Series — 1 if festival, 0 otherwise.
                          Used only for per-regime MAPE logging; does not affect weights.

        Returns:
            self (for chaining)
        """
        t0 = time.perf_counter()
        n_models   = len(self.models)
        n_rows     = len(X)
        n_features = X.shape[1]

        logger.info(
            f"[AgentEnsemble] fit() start — "
            f"{n_models} models, {n_rows} rows, {n_features} features, "
            f"n_splits={self.n_splits}, top_n={self.top_n}"
        )

        if regime_flags is None:
            regime_flags = pd.Series(np.zeros(len(y)), index=y.index)

        X_clean = X.fillna(0)

        # ── Step 2a: Walk-forward CV for every model ────────────────── #
        cv_results: Dict[str, Dict[str, Any]] = {}

        for model_name, model in self.models.items():
            fold_mapes: List[float]      = []
            fold_fest_mapes: List[float] = []
            fold_predictions: List[np.ndarray] = []
            last_fold_model = None

            tscv = TimeSeriesSplit(n_splits=self.n_splits)

            for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X_clean)):
                X_tr = X_clean.iloc[train_idx]
                y_tr = y.iloc[train_idx]
                X_te = X_clean.iloc[test_idx]
                y_te = y.iloc[test_idx]
                regime_te = regime_flags.iloc[test_idx]

                # Each fold gets a fresh deep-copy — no state leakage across folds
                fold_model = copy.deepcopy(model)

                try:
                    fold_model.fit(X_tr, y_tr)
                    preds = fold_model.predict(X_te)

                    # ── NaN / Inf guard ──────────────────────────────── #
                    if np.any(~np.isfinite(preds)):
                        logger.warning(
                            f"[AgentEnsemble][{model_name}] Fold {fold_idx}: "
                            f"{np.sum(~np.isfinite(preds))} non-finite predictions — "
                            "replacing with y_train mean."
                        )
                        preds = np.full_like(preds, float(y_tr.mean()), dtype=float)

                    # ── MAPE guard: skip fold if all actuals are zero ── #
                    y_te_arr = y_te.values
                    if np.all(y_te_arr == 0):
                        logger.debug(
                            f"[AgentEnsemble][{model_name}] Fold {fold_idx}: "
                            "all actuals are zero — skipping MAPE."
                        )
                        last_fold_model = fold_model
                        continue

                    mape = mean_absolute_percentage_error(y_te_arr, preds)
                    fold_mapes.append(float(mape))
                    fold_predictions.append(preds)

                    # Festival sub-regime MAPE
                    fest_mask = regime_te.values == 1
                    if fest_mask.sum() > 0 and not np.all(y_te_arr[fest_mask] == 0):
                        fold_fest_mapes.append(
                            float(mean_absolute_percentage_error(
                                y_te_arr[fest_mask], preds[fest_mask]
                            ))
                        )

                    last_fold_model = fold_model

                except Exception as exc:
                    logger.warning(
                        f"[AgentEnsemble][{model_name}] Fold {fold_idx} failed: {exc}. "
                        "Assigning MAPE=999."
                    )
                    fold_mapes.append(999.0)

            # Record CV results
            if fold_mapes and last_fold_model is not None:
                avg_mape      = float(np.mean(fold_mapes))
                avg_fest_mape = float(np.mean(fold_fest_mapes)) if fold_fest_mapes else avg_mape

                logger.info(
                    f"[AgentEnsemble][{model_name}] CV done — "
                    f"avg_MAPE={avg_mape:.4f}, "
                    f"festival_MAPE={avg_fest_mape:.4f}, "
                    f"folds={len(fold_mapes)}"
                )

                cv_results[model_name] = {
                    "avg_mape":       avg_mape,
                    "fest_mape":      avg_fest_mape,
                    "fold_mapes":     fold_mapes,
                    "last_fold_model": last_fold_model,
                }
            else:
                logger.warning(
                    f"[AgentEnsemble][{model_name}] All folds failed — excluded from ensemble."
                )

        if not cv_results:
            raise RuntimeError(
                "AgentEnsemble: all models failed walk-forward CV. "
                "Check data quality and model compatibility."
            )

        # ── Step 3: Weight calculation ───────────────────────────────── #
        #   weight_i = (1 / MAPE_i) / Σ_j (1 / MAPE_j)
        #   Cap individual model MAPE at 999 to prevent div-by-zero dominance.
        ranked = sorted(cv_results.items(), key=lambda x: x[1]["avg_mape"])
        top_n_results = ranked[: self.top_n]

        # Compute raw inverse-MAPE weights
        raw_weights: Dict[str, float] = {
            name: 1.0 / (res["avg_mape"] + 1e-9)
            for name, res in top_n_results
        }
        total_inv = sum(raw_weights.values()) + 1e-12

        normalised_weights: Dict[str, float] = {
            name: w / total_inv for name, w in raw_weights.items()
        }

        # Drop models below min_weight_threshold and renormalise
        active_weights = {
            name: w for name, w in normalised_weights.items()
            if w >= self.min_weight_threshold
        }
        if not active_weights:
            # Safety: if all weights are tiny (very flat MAPE), keep the best
            best_name = top_n_results[0][0]
            active_weights = {best_name: 1.0}

        total_active = sum(active_weights.values()) + 1e-12
        self.weights = {name: w / total_active for name, w in active_weights.items()}

        # Store errors and per-fold errors for audit
        self.errors = {name: cv_results[name]["avg_mape"]
                       for name in self.weights}
        self.cv_fold_errors = {name: cv_results[name]["fold_mapes"]
                               for name in self.weights}

        logger.info(
            f"[AgentEnsemble] Final weights ({len(self.weights)} models): "
            + ", ".join(f"{n}={w:.4f}" for n, w in self.weights.items())
        )

        # ── Full-data refit for best inference ───────────────────────── #
        self._fitted_models = {}
        for name in self.weights:
            full_model = copy.deepcopy(self.models[name])
            try:
                full_model.fit(X_clean, y)
                self._fitted_models[name] = full_model
                logger.debug(f"[AgentEnsemble][{name}] Full-data refit complete.")
            except Exception as exc:
                logger.warning(
                    f"[AgentEnsemble][{name}] Full-data refit failed: {exc}. "
                    "Falling back to last CV fold model."
                )
                self._fitted_models[name] = cv_results[name]["last_fold_model"]

        elapsed = time.perf_counter() - t0
        self._fit_metadata = {
            "fitted_at":        datetime.utcnow().isoformat() + "Z",
            "n_rows":           n_rows,
            "n_features":       n_features,
            "n_models_total":   n_models,
            "n_models_active":  len(self.weights),
            "fit_duration_sec": round(elapsed, 3),
            "cv_n_splits":      self.n_splits,
        }
        self._is_fitted = True
        logger.info(
            f"[AgentEnsemble] fit() complete — "
            f"{len(self._fitted_models)} active models, "
            f"elapsed={elapsed:.2f}s"
        )
        return self

    # ================================================================== #
    #  Step 4 — Prediction                                                #
    # ================================================================== #
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute weighted ensemble prediction.

        Stores per-model predictions in self.last_predictions (dict of
        {model_name: ndarray}) for logging and explainability.

        Args:
            X: Feature DataFrame for prediction rows.

        Returns:
            1-D numpy array of weighted predictions.
        """
        if not self._is_fitted:
            raise RuntimeError(
                "AgentEnsemble.predict() called before fit(). "
                "Call fit(X, y) first."
            )

        X_clean = X.fillna(0)
        ensemble_preds = np.zeros(len(X_clean))
        self.last_predictions = {}

        for name, model in self._fitted_models.items():
            w = self.weights.get(name, 0.0)
            if w <= 0:
                continue
            try:
                preds = model.predict(X_clean)
                if not np.all(np.isfinite(preds)):
                    logger.warning(
                        f"[AgentEnsemble][{name}] Non-finite predictions at inference — skipping."
                    )
                    continue
                self.last_predictions[name] = preds
                ensemble_preds += preds * w
            except Exception as exc:
                logger.warning(
                    f"[AgentEnsemble][{name}] predict() failed at inference: {exc}. Skipping."
                )

        # Scalar shortcut for single-row prediction (most common agent use-case)
        if len(ensemble_preds) == 1:
            self.last_ensemble_prediction = float(ensemble_preds[0])
        else:
            self.last_ensemble_prediction = None   # multi-row; caller handles

        return ensemble_preds

    # ================================================================== #
    #  Step 6 — Logging                                                   #
    # ================================================================== #
    def get_ensemble_log(self) -> Dict[str, Any]:
        """
        Return a fully serialisable audit dict capturing the ensemble state.

        This dict is designed to be injected directly into AgentOutput.metadata
        so the entire ensemble decision trail is preserved in the output record.

        Keys:
          fit_metadata          – timing, data dimensions, n_models
          model_weights         – normalised weight per active model
          model_errors          – avg CV MAPE per active model
          model_cv_fold_errors  – per-fold MAPE list per model (for diagnostics)
          last_predictions      – scalar prediction from each model at last predict()
          last_ensemble_pred    – the final weighted prediction scalar
          ranked_models         – models sorted by ascending MAPE
        """
        if not self._is_fitted:
            return {"status": "unfitted", "models": list(self.models.keys())}

        # Convert ndarray predictions to scalar / list for JSON serialisability
        serialised_preds: Dict[str, Any] = {}
        for name, preds in self.last_predictions.items():
            if hasattr(preds, "__len__") and len(preds) == 1:
                serialised_preds[name] = round(float(preds[0]), 6)
            elif hasattr(preds, "__len__"):
                serialised_preds[name] = [round(float(p), 6) for p in preds]
            else:
                serialised_preds[name] = round(float(preds), 6)

        ranked_models = sorted(self.errors.items(), key=lambda x: x[1])

        return {
            "fit_metadata":         self._fit_metadata,
            "model_weights":        {n: round(w, 6) for n, w in self.weights.items()},
            "model_errors":         {n: round(e, 6) for n, e in self.errors.items()},
            "model_cv_fold_errors": {
                n: [round(e, 6) for e in folds]
                for n, folds in self.cv_fold_errors.items()
            },
            "last_predictions":     serialised_preds,
            "last_ensemble_pred":   round(self.last_ensemble_prediction, 6)
                                    if self.last_ensemble_prediction is not None else None,
            "ranked_models":        [(n, round(e, 6)) for n, e in ranked_models],
        }

    # ================================================================== #
    #  Convenience properties                                             #
    # ================================================================== #
    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def n_active_models(self) -> int:
        return len(self._fitted_models)

    @property
    def best_model_name(self) -> Optional[str]:
        """Name of the model with the lowest CV MAPE."""
        if not self.errors:
            return None
        return min(self.errors, key=self.errors.get)

    def __repr__(self) -> str:
        status = f"fitted, {self.n_active_models} models" if self._is_fitted else "unfitted"
        return f"<AgentEnsemble [{status}] | top_n={self.top_n}, n_splits={self.n_splits}>"
