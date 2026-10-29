"""Train the market-choice engine for every crop with enough market history.

    python scripts/build_market_choice.py                 # all crops
    python scripts/build_market_choice.py --crops tomato  # one crop

Reads  mandisense_ai/data/farmer/market_daily.parquet   (built by build_farmer_world.py --ingest)
Writes mandisense_ai/models/market_choice/<crop>/{model.joblib, meta.json, scores.npy, sigma.npy}

Each crop is trained on realised-outcome labels, backtested walk-forward on its most recent ~16 months
and calibrated for the conformal revenue floor; the backtest travels with the model and is shown in the app.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.market_choice.engine import train_all  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crops", nargs="*")
    args = ap.parse_args()
    res = train_all(args.crops)
    for crop, meta in res.items():
        if not meta:
            print(f"{crop:8s} skipped (not enough markets or history)")
            continue
        bt = meta["backtest"]
        if bt.get("status") != "OK":
            print(f"{crop:8s} {meta['n_markets']} mandis; backtest {bt.get('status')}")
            continue
        rev = bt["mean_net_revenue"]
        print(f"{crop:8s} {meta['n_markets']:2d} mandis | recommended Rs{rev['recommended']:.0f} vs highest-yday Rs{rev['highest_yesterday']:.0f}, "
              f"nearest Rs{rev['nearest']:.0f}, safest Rs{rev['safest']:.0f}, oracle Rs{rev['oracle']:.0f}\n"
              f"         gain vs highest-yday {bt['gain_vs_highest_yesterday']} | evidence: {bt['evidence_level']} "
              f"| floor violation adaptive {bt['floor_violation_adaptive']} static-OOS {bt['floor_violation_static_out_of_sample']} | silent trips {bt['silent_trip_rate']}")
    print(json.dumps({c: (m["backtest"].get("status") if m else None) for c, m in res.items()}))


if __name__ == "__main__":
    main()
