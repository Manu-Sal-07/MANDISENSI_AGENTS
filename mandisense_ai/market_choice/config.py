"""Constants and assumptions of the market-choice engine.

Everything that is an *assumption* about the farmer's costs lives in
`Economics` and is returned with every recommendation, so a farmer who knows
his own truck is cheaper or dearer can see how the answer would move.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict

from mandisense_ai.farmer import world

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PACKAGE_ROOT / "models" / "market_choice"
EVIDENCE_DIR = PACKAGE_ROOT / "data" / "market_choice"
EVIDENCE_FILE = EVIDENCE_DIR / "evidence.json"
PANEL_FILE = world.MARKET_PANEL

K_MAX = 3                      # a farmer may hold up to 3 days
N_HOLD = K_MAX + 1
MAX_STALENESS = 14             # a mandi silent for longer is not offered
MIN_REPORTED_DAYS = 400        # a mandi needs this many reported days to be a candidate
MIN_MARKETS = 2                # fewer than this and there is no choice to make
EVIDENCE_MARKETS = 3           # fewer than this and the crop is flagged as limited evidence
WARMUP_DAYS = 60
GAP_DAYS = K_MAX + 2           # separation between training data and the block it predicts

CALIBRATION_WINDOW = 365       # resolved scores kept for the conformal quantile
DEFAULT_ALPHA = 0.10
ALPHAS = (0.05, 0.10, 0.20)

# Daily value lost while holding. A scenario assumption by crop, not an estimate.
CROP_SPOILAGE: Dict[str, float] = {"tomato": 0.03, "ginger": 0.008, "onion": 0.008, "potato": 0.004, "garlic": 0.003}


@dataclass(frozen=True)
class Economics:
    """Net revenue per quintal of selling at yard m after k days of holding.

        R = (1 - fee) (1 - spoilage)^k P  -  transport * road * km  -  handling

    If the chosen yard turns out silent on the sale day the farmer still pays
    for the trip and sells at `silent_price_factor` times the day's mean
    reported price (the assumption that makes silence costly).
    """

    transport_per_q_km: float = 0.70    # Rs per quintal per road-km (small tempo; full trucks are ~0.35)
    road_factor: float = 1.3
    market_fee: float = 0.04
    handling: float = 20.0
    spoilage_per_day: float = 0.03
    silent_price_factor: float = 0.85
    farmgate_factor: float = 0.80

    def but(self, **kw) -> "Economics":
        return replace(self, **kw)


def economics_for(crop: str, transport_per_q_km: float | None = None) -> Economics:
    e = Economics(spoilage_per_day=CROP_SPOILAGE.get(crop, 0.01))
    return e.but(transport_per_q_km=transport_per_q_km) if transport_per_q_km is not None else e


# Vehicle presets shown in the farmer UI (Rs per quintal-km).
TRANSPORT_PRESETS = {"shared_truck": 0.35, "tempo": 0.70, "small_pickup": 1.40}
