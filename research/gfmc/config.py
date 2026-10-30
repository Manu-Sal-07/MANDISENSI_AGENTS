"""Central configuration for the GFMC study.

Everything that is an *assumption* (as opposed to data) lives in `Economics`
so that it can be reported, swept and criticised in one place. Nothing here is
fitted to the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DATA_DIR = REPO / "datasets" / "year_data"
HISTORY_GLOB = "historical_data/All_Type_of_Report*.csv"
DAILY_GLOB = "Daily Price Arrival Report*.csv"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = RESULTS_DIR / "cache"

SEED = 20261028

# Horizons: the farmer decides on the morning of day t knowing data through t-1.
# Action "hold k days" sells on day t+k, k = 0..K_MAX (price horizon h = k+1).
K_MAX = 3
N_HOLD = K_MAX + 1

PRIMARY_CROP = "Tomato"
SECONDARY_CROPS: Tuple[str, ...] = ("Onion", "Potato", "Ginger")
# Garlic is not studied: only one mandi in the belt (Bengaluru) has MIN_REPORTED_DAYS reported days, so there is no choice between markets to learn.
# A crop's name in the Agmarknet export where it differs from the name used here:
SOURCE_CROP_NAME = {"Ginger": "Ginger(Green)"}

MIN_REPORTED_DAYS = 700          # a market must have this many reported days to be a candidate
MAX_STALENESS_ELIGIBLE = 14      # a market silent for longer is not offered to the farmer
WARMUP_DAYS = 60                 # feature warm-up before the first decision day

# Outer walk-forward test blocks [start, end). Each is scored out of sample.
OUTER_FOLDS: Tuple[Tuple[str, str], ...] = (
    ("2024-01-01", "2024-07-01"),
    ("2024-07-01", "2025-01-01"),
    ("2025-01-01", "2025-07-01"),
    ("2025-07-01", "2026-01-01"),
    ("2026-01-01", "2026-10-28"),
)


@dataclass(frozen=True)
class Economics:
    """Scenario parameters of the farmer's net-revenue function (per quintal).

    These are assumptions, not estimates: `transport_per_q_km` is anchored on
    published freight levels (about Rs 0.2-0.4 per quintal-km for trucked
    vegetables; a TNAU study cites ~Rs 240/q for a long haul) and every result
    is re-run over a sweep (see `SWEEPS`).
    """

    transport_per_q_km: float = 0.35   # Rs per quintal per road-km
    road_factor: float = 1.3           # road distance / great-circle distance
    market_fee: float = 0.04           # commission + market fee, share of sale value
    handling: float = 20.0             # Rs/q loading + unloading, fixed per trip
    spoilage_per_day: float = 0.03     # share of value lost per day of holding (tomato)
    fallback_discount: float = 0.85    # phi: price if the chosen mandi did not report
    farmgate_discount: float = 0.80    # phi_g: selling to a local trader at the gate

    def but(self, **kw) -> "Economics":
        return replace(self, **kw)


DEFAULT_ECON = Economics()

# Daily value loss while holding, by crop (scenario assumption; tomato is the
# most perishable of the three, potato the least).
# Ginger follows the shelf-life table the application uses for farmers (mandisense_ai/farmer/reference.py: 1.5% a day).
CROP_SPOILAGE = {"Tomato": 0.03, "Onion": 0.008, "Potato": 0.004, "Ginger": 0.015}

# One-at-a-time sensitivity sweeps for the economic assumptions.
SWEEPS = {
    "transport_per_q_km": (0.20, 0.35, 0.70, 1.40),
    "spoilage_per_day": (0.01, 0.03, 0.06),
    "fallback_discount": (0.70, 0.85, 1.00),
}

# Approximate coordinates for markets absent from the application's registry.
# Only used for the three sparse Tumakuru-district markets, which fall below
# MIN_REPORTED_DAYS and are therefore not offered as actions.
EXTRA_MARKET_COORDS = {
    "Tumakuru APMC": (13.3392, 77.1140),
    "Gubbi APMC": (13.3125, 76.9400),
    "Madhugiri APMC": (13.6600, 77.2100),
}


@dataclass(frozen=True)
class Conformal:
    alpha: float = 0.10        # target floor-violation rate
    gamma: float = 0.01        # adaptive-conformal step size
    window: int = 365          # score window for the empirical quantile
    min_scores: int = 30       # below this, fall back to a conservative quantile
    delay_max: int = K_MAX     # outcome of a k-day hold is known k days late


DEFAULT_CONFORMAL = Conformal()
