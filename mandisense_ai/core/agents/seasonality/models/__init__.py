"""
Seasonality Model Pool — public registry.

Import from this module to get the complete dict of {name: model_instance}
that TieredModelPipeline uses.  Keeping registration here means adding a new
model is a one-line change: just import and add to MODEL_REGISTRY.
"""

from core.agents.seasonality.models.stl_linear import STLLinearRegressionModel
from core.agents.seasonality.models.random_forest import RandomForestSeasonalityModel
from core.agents.seasonality.models.xgboost_model import XGBoostSeasonalityModel
from core.agents.seasonality.models.lightgbm_model import LightGBMSeasonalityModel
from core.agents.seasonality.models.ridge_model import RidgeSeasonalityModel
from core.agents.seasonality.models.lasso_model import LassoSeasonalityModel
from core.agents.seasonality.models.moving_average import MovingAverageBaselineModel
from core.agents.seasonality.models.lag_linear import LagLinearModel
from core.agents.seasonality.models.sarima_model import SARIMASeasonalityModel

# -----------------------------------------------------------------------
# SEASONALITY_MODEL_REGISTRY
# -----------------------------------------------------------------------
# Key  = model name used in weight_registry.json and model_contributions dict
# Value = a fresh (unfitted) model instance
#
# Notes:
#   - SARIMA is included but will self-degrade (via fallback mean) if the
#     dataset is too short or statsmodels convergence fails — it will simply
#     receive a low ensemble weight.
#   - To disable a model, comment it out here; no other files need changing.
# -----------------------------------------------------------------------

SEASONALITY_MODEL_REGISTRY: dict = {
    STLLinearRegressionModel.model_name:   STLLinearRegressionModel(),
    RandomForestSeasonalityModel.model_name: RandomForestSeasonalityModel(),
    XGBoostSeasonalityModel.model_name:    XGBoostSeasonalityModel(),
    LightGBMSeasonalityModel.model_name:   LightGBMSeasonalityModel(),
    RidgeSeasonalityModel.model_name:      RidgeSeasonalityModel(),
    LassoSeasonalityModel.model_name:      LassoSeasonalityModel(),
    MovingAverageBaselineModel.model_name: MovingAverageBaselineModel(),
    LagLinearModel.model_name:             LagLinearModel(),
    SARIMASeasonalityModel.model_name:     SARIMASeasonalityModel(),   # optional 9th
}

__all__ = [
    "SEASONALITY_MODEL_REGISTRY",
    "STLLinearRegressionModel",
    "RandomForestSeasonalityModel",
    "XGBoostSeasonalityModel",
    "LightGBMSeasonalityModel",
    "RidgeSeasonalityModel",
    "LassoSeasonalityModel",
    "MovingAverageBaselineModel",
    "LagLinearModel",
    "SARIMASeasonalityModel",
]
