"""
Gaussian Hidden Markov Model for Market Regime Classification.

Detects 4 regimes: Stable, Medium, Volatile, Crisis.
States are auto-sorted by mean volatility after fitting.

Performance: Training <10s, Prediction <50ms, Persistence >0.7
"""

from __future__ import annotations
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
try:
    from mandisense_ai.utils.logger import get_logger
except ImportError:
    from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

FEATURE_COLUMNS = ["garch_volatility", "realized_volatility", "momentum", "volume_stress"]
REGIME_NAMES = {1: "Stable", 2: "Medium Volatility", 3: "High Volatility", 4: "Crisis"}


class HMMRegimeClassifier:
    """4-state Gaussian HMM for market regime classification."""

    def __init__(self, n_states: int = 4, n_iter: int = 100, random_state: int = 42):
        self.n_states = n_states
        self.model = hmm.GaussianHMM(
            n_components=n_states, covariance_type="full",
            n_iter=n_iter, random_state=random_state, verbose=False,
        )
        self.feature_scaler = StandardScaler()
        self.fitted = False

    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Construct and scale feature matrix for HMM."""
        missing = set(FEATURE_COLUMNS) - set(data.columns)
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")
        features = data[FEATURE_COLUMNS].values.copy()
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        if not self.fitted:
            scaled = self.feature_scaler.fit_transform(features)
        else:
            scaled = self.feature_scaler.transform(features)
        return scaled

    def fit(self, features: np.ndarray) -> None:
        """Fit HMM on historical features, then auto-sort states by volatility."""
        logger.info(f"[HMMClassifier] Fitting {self.n_states}-state HMM on {len(features)} obs")
        self.model.fit(features)
        self.fitted = True
        self._sort_states_by_volatility()
        stats = self.get_state_statistics()
        for state, stat in stats.items():
            logger.info(
                f"[HMMClassifier] State {state} ({REGIME_NAMES[state]}): "
                f"mu_vol={stat['mean_volatility']:.4f}, persistence={stat['persistence']:.3f}"
            )

    def _sort_states_by_volatility(self) -> None:
        """Re-order states: State 1 = lowest vol, State 4 = highest vol."""
        vol_means = self.model.means_[:, 0]
        idx = np.argsort(vol_means)
        self.model.transmat_ = self.model.transmat_[idx, :][:, idx]
        self.model.means_ = self.model.means_[idx, :]
        # Bypass hmmlearn's covars_ setter validation — the covariances are
        # already valid, we are only re-ordering existing components.
        self.model._covars_ = self.model._covars_[idx, :]
        self.model.startprob_ = self.model.startprob_[idx]

    def predict_regime(self, features: np.ndarray) -> Tuple[int, float]:
        """Predict current regime (1-4) and transition probability."""
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction.")
        states = self.model.predict(features)
        current_state = int(states[-1]) + 1
        if len(states) > 1:
            prev = int(states[-2])
            transition_prob = float(self.model.transmat_[prev, states[-1]])
        else:
            transition_prob = 1.0
        return current_state, transition_prob

    def get_regime_probabilities(self, features: np.ndarray) -> np.ndarray:
        """Posterior probability distribution over all regimes for last obs."""
        if not self.fitted:
            raise ValueError("Model must be fitted first.")
        _, posteriors = self.model.score_samples(features)
        return posteriors[-1, :]

    def get_state_statistics(self) -> Dict[int, Dict]:
        """Return mean volatility, momentum, persistence, and transition probs per state."""
        if not self.fitted:
            raise ValueError("Model must be fitted first.")
        stats: Dict[int, Dict] = {}
        for s in range(self.n_states):
            stats[s + 1] = {
                "name": REGIME_NAMES.get(s + 1, f"State {s+1}"),
                "mean_volatility": float(self.model.means_[s, 0]),
                "mean_momentum": float(self.model.means_[s, 2]) if self.model.means_.shape[1] > 2 else 0.0,
                "persistence": float(self.model.transmat_[s, s]),
                "transition_probs": self.model.transmat_[s, :].tolist(),
            }
        return stats

    def predict_state_sequence(self, features: np.ndarray) -> np.ndarray:
        """Full Viterbi state sequence (1-indexed)."""
        if not self.fitted:
            raise ValueError("Model must be fitted first.")
        return self.model.predict(features) + 1

    def save(self, path: str) -> None:
        """Save fitted HMM + scaler via joblib."""
        import joblib
        if not self.fitted:
            raise ValueError("Cannot save unfitted model.")
        joblib.dump({"model": self.model, "scaler": self.feature_scaler, "n_states": self.n_states}, path)
        logger.info(f"[HMMClassifier] Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> "HMMRegimeClassifier":
        """Load a previously saved model."""
        import joblib
        data = joblib.load(path)
        instance = cls(n_states=data["n_states"])
        instance.model = data["model"]
        instance.feature_scaler = data["scaler"]
        instance.fitted = True
        return instance

    def __repr__(self) -> str:
        status = "fitted" if self.fitted else "unfitted"
        return f"<HMMRegimeClassifier [{status}] n_states={self.n_states}>"
