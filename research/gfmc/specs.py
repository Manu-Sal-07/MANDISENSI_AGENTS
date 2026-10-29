"""Model specifications and their hyper-parameter search spaces.

Each spec fully determines one compared method: model family, training
labels, loss, feature groups, and what its hyper-parameters are tuned on.

``tune_on``:
    "regret"  validation decision regret (plug-in argmax policy) - "tune for the decision"
    "mse"     validation Huber loss on the model's native labels - the usual practice
    "none"    no tuning (benchmarks)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

from gfmc.models.base import PriceModel, RandomWalk
from gfmc.models.gbm import LGBMModel, XGBModel
from gfmc.models.neural import DeepSetsModel


@dataclass(frozen=True)
class Spec:
    name: str
    family: str                     # rw | lgbm | xgb | deepsets
    groups: Tuple[str, ...]         # feature groups used
    tune_on: str = "regret"
    labels: str = "observed"        # observed | filled   (GBM) - neural uses `loss`
    loss: str = "spo"               # neural only: mse_obs | mse_filled | spo
    structured: bool = False
    note: str = ""

    @property
    def native_labels(self) -> str:
        """Which labels the model is trained on, for the 'mse' tuning objective."""
        if self.family in ("lgbm", "xgb"):
            return self.labels
        return "observed" if self.loss == "mse_obs" else "filled"


def suggest(spec: Spec, trial) -> Dict:
    f = spec.family
    if f == "lgbm":
        return dict(n_estimators=trial.suggest_int("n_estimators", 100, 500, step=50),
                    learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                    num_leaves=trial.suggest_int("num_leaves", 4, 48),
                    min_child_samples=trial.suggest_int("min_child_samples", 20, 120),
                    subsample=trial.suggest_float("subsample", 0.6, 1.0),
                    colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
                    reg_lambda=trial.suggest_float("reg_lambda", 0.1, 30.0, log=True),
                    huber_delta=trial.suggest_float("huber_delta", 0.05, 0.4))
    if f == "xgb":
        return dict(n_estimators=trial.suggest_int("n_estimators", 100, 500, step=50),
                    learning_rate=trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                    max_depth=trial.suggest_int("max_depth", 2, 6),
                    min_child_weight=trial.suggest_int("min_child_weight", 3, 40),
                    subsample=trial.suggest_float("subsample", 0.6, 1.0),
                    colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
                    reg_lambda=trial.suggest_float("reg_lambda", 0.1, 30.0, log=True))
    if f == "deepsets":
        hp = dict(hidden=trial.suggest_categorical("hidden", [32, 64, 128]),
                  depth=trial.suggest_int("depth", 1, 3),
                  dropout=trial.suggest_float("dropout", 0.0, 0.3),
                  emb=trial.suggest_categorical("emb", [2, 4, 8]),
                  lr=trial.suggest_float("lr", 5e-4, 1e-2, log=True),
                  weight_decay=trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True),
                  epochs=trial.suggest_categorical("epochs", [30, 60, 90]),
                  batch=trial.suggest_categorical("batch", [32, 64, 128]),
                  huber=trial.suggest_float("huber", 0.05, 0.4))
        if spec.loss == "spo":
            hp["aux"] = trial.suggest_float("aux", 0.05, 2.0, log=True)
        if spec.structured:
            hp["w_rep"] = trial.suggest_float("w_rep", 0.1, 2.0, log=True)
        return hp
    return {}


def build(spec: Spec, hp: Dict, n_seeds: int = 1) -> PriceModel:
    if spec.family == "rw":
        return RandomWalk()
    if spec.family == "lgbm":
        return LGBMModel(labels=spec.labels, name=spec.name, **hp)
    if spec.family == "xgb":
        m = XGBModel(**hp)
        m.name = spec.name
        return m
    if spec.family == "deepsets":
        return DeepSetsModel(loss=spec.loss, structured=spec.structured, n_seeds=n_seeds, name=spec.name, **hp)
    raise KeyError(spec.family)


B, BS = ("base",), ("base", "silence")

SPECS: Tuple[Spec, ...] = (
    Spec("rw", "rw", B, "none", note="random walk, cost-aware plug-in"),
    Spec("lgbm_obs", "lgbm", B, "mse", labels="observed", note="predict-then-optimise, observed labels"),
    Spec("xgb_obs", "xgb", B, "mse", labels="observed", note="predict-then-optimise, observed labels"),
    Spec("lgbm_filled", "lgbm", B, "regret", labels="filled", note="GBM on realised-revenue labels"),
    Spec("lgbm_filled_sil", "lgbm", BS, "regret", labels="filled", note="+ network silence features"),
    Spec("ds_mse_obs", "deepsets", B, "mse", loss="mse_obs", note="neural, observed-label MSE"),
    Spec("ds_mse_filled", "deepsets", B, "regret", loss="mse_filled", note="neural, realised-label MSE"),
    Spec("ds_spo", "deepsets", B, "regret", loss="spo", note="neural, SPO+ decision loss"),
    Spec("ds_spo_struct", "deepsets", B, "regret", loss="spo", structured=True, note="SPO+ + reporting head"),
    Spec("gfmc_pred", "deepsets", BS, "regret", loss="spo", structured=True,
         note="proposed predictor: SPO+ + reporting head + silence features"),
    Spec("gfmc_pred_tuneMSE", "deepsets", BS, "mse", loss="spo", structured=True,
         note="ablation: same model tuned on forecast loss instead of decision regret"),
)

SPEC_BY_NAME = {s.name: s for s in SPECS}
