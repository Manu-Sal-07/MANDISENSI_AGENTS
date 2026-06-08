"""
Arrival Model Pool — public registry.

Import ARRIVAL_MODEL_REGISTRY to get the complete dict of {name: model_instance}
used by ArrivalVolumeAgent's ensemble pipeline.

Adding a new model = 1 import + 1 registry line.  No other changes needed.
"""

from mandisense_ai.core.agents.arrival.models.xgboost_model import XGBoostArrivalModel
from mandisense_ai.core.agents.arrival.models.random_forest import RandomForestArrivalModel
from mandisense_ai.core.agents.arrival.models.elasticity_linear import ElasticityLinearArrivalModel
from mandisense_ai.core.agents.arrival.models.ridge_model import RidgeArrivalModel
from mandisense_ai.core.agents.arrival.models.lasso_model import LassoArrivalModel
from mandisense_ai.core.agents.arrival.models.gradient_boosting import GradientBoostingArrivalModel
from mandisense_ai.core.agents.arrival.models.simple_baseline import SimpleBaselineArrivalModel
from mandisense_ai.core.agents.arrival.models.polynomial_model import PolynomialArrivalModel

# -----------------------------------------------------------------------
# ARRIVAL_MODEL_REGISTRY
# -----------------------------------------------------------------------
# Key  = model name used in weight_registry.json and model_contributions dict
# Value = a fresh (unfitted) model instance
#
# Notes:
#   - PolynomialRegression is included but may receive low weight on large
#     datasets where gradient boosters dominate. It shines on small mandis.
#   - To disable a model, comment it out here.
# -----------------------------------------------------------------------

ARRIVAL_MODEL_REGISTRY: dict = {
    XGBoostArrivalModel.model_name:         XGBoostArrivalModel(),
    RandomForestArrivalModel.model_name:    RandomForestArrivalModel(),
    ElasticityLinearArrivalModel.model_name: ElasticityLinearArrivalModel(),
    RidgeArrivalModel.model_name:           RidgeArrivalModel(),
    LassoArrivalModel.model_name:           LassoArrivalModel(),
    GradientBoostingArrivalModel.model_name: GradientBoostingArrivalModel(),
    SimpleBaselineArrivalModel.model_name:  SimpleBaselineArrivalModel(),
    PolynomialArrivalModel.model_name:      PolynomialArrivalModel(),   # optional 8th
}

__all__ = [
    "ARRIVAL_MODEL_REGISTRY",
    "XGBoostArrivalModel",
    "RandomForestArrivalModel",
    "ElasticityLinearArrivalModel",
    "RidgeArrivalModel",
    "LassoArrivalModel",
    "GradientBoostingArrivalModel",
    "SimpleBaselineArrivalModel",
    "PolynomialArrivalModel",
]
