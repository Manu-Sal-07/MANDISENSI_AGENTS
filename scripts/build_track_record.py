"""
Build the public track record of the served market-choice advice.

    python scripts/build_track_record.py [crop ...]

Replays the walk-forward back-test with day-by-day output and writes
`mandisense_ai/models/market_choice/<crop>/track_record.json`. The back-test is the same code that produced the served
engines' evidence, so its headline numbers must reproduce `meta.json`; the script checks this and refuses to write a record
that disagrees (a record that cannot be reproduced is not a record).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mandisense_ai.market_choice.config import ARTIFACT_DIR, economics_for  # noqa: E402
from mandisense_ai.market_choice.engine import backtest, build_dataset  # noqa: E402
from mandisense_ai.market_choice.panel import build_panel, load_long  # noqa: E402


def main(crops) -> int:
    long = load_long()
    bad = 0
    for crop in crops:
        meta_path = ARTIFACT_DIR / crop / "meta.json"
        if not meta_path.exists():
            print(f"{crop}: no served engine, skipped")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        dd = build_dataset(build_panel(long, crop))
        bt = backtest(dd, economics_for(crop), daily=True)
        want, got = meta["backtest"]["mean_net_revenue"], bt["mean_net_revenue"]
        if any(abs(want[k] - got[k]) > 0.15 for k in want):
            print(f"{crop}: MISMATCH with meta.json {want} vs {got}; not written")
            bad += 1
            continue
        d = bt["_daily"]
        days = d["days"]
        near = [x["recommended"] - x["nearest"] for x in days]
        high = [x["recommended"] - x["highest_yesterday"] for x in days]

        def wtl(g):
            n_ = len(g)
            return {"win": round(sum(v > 1 for v in g) / n_, 3), "tie": round(sum(abs(v) <= 1 for v in g) / n_, 3),
                    "loss": round(sum(v < -1 for v in g) / n_, 3), "mean": round(sum(g) / n_, 1)}

        def window(k):
            sl = slice(-k, None) if k else slice(None)
            return {"days": len(days[sl]), "vs_nearest": wtl(near[sl]), "vs_highest_yesterday": wtl(high[sl]),
                    "floor_held_share": round(sum(x["floor_held"] for x in days[sl]) / len(days[sl]), 3)}

        out = {
            "crop": crop, "window": [days[0]["date"], days[-1]["date"]], "days": days, "alpha": 0.10,
            "alpha_effective": d["alpha_effective"], "floor_multiplier": d["q"],
            "last60": window(60), "all": window(0),
            "note": "Out-of-sample days only: the floor multiplier was fitted on earlier days. Revenue is Rs per quintal after transport, "
                    "fees and spoilage, averaged over five farmer origins.",
        }
        (ARTIFACT_DIR / crop / "track_record.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"{crop}: {len(days)} days written; all: {out['all']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:] or ["tomato", "onion", "potato", "ginger"]))
