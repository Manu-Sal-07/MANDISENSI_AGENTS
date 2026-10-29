"""
Build the supply-shock study artifact (own-crop price response to arrival gluts and squeezes),
and bundle it with the cross-commodity and district-gap results already in the transmission matrix.

    python scripts/build_shock_study.py

Reads   mandisense_ai/data/farmer/district_observations.parquet
        mandisense_ai/models/farmer/transmission_matrix.json   (scripts/build_transmission.py)
Writes  mandisense_ai/models/shock/shock_study.json
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.farmer import world  # noqa: E402
from mandisense_ai.shock.study import run_study  # noqa: E402

OUT = PROJECT_ROOT / "mandisense_ai" / "models" / "shock" / "shock_study.json"


def main() -> None:
    obs = world.district_observations()
    if obs.empty:
        raise SystemExit("district observations missing; run scripts/build_farmer_world.py --ingest first")
    t0 = time.time()
    study = run_study(obs)
    matrix = world.transmission_matrix()
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {"from": str(obs["date"].min().date()), "to": str(obs["date"].max().date()),
                 "crops": sorted(obs["commodity"].unique().tolist()), "districts": sorted(obs["mandi_id"].unique().tolist())},
        "own_crop": study,
        "cross_commodity": matrix.get("test_a_cross_commodity") if matrix.get("available") else None,
        "district_gaps": matrix.get("test_b_spatial_gaps") if matrix.get("available") else None,
        "neighbour_signal": matrix.get("neighbour_signal") if matrix.get("available") else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT.name} in {time.time() - t0:.0f}s: tested {study['n_tested']}, robust {study['n_robust']}, suggestive {study['n_suggestive']}")
    for r in study["results"]:
        if r["status"] == "OK" and r["tier"] != "NONE":
            print(f"  {r['tier']:10s} {r['crop']:7s} {r['direction']:7s} h={r['horizon']:2d}d n={r['n']:3d} effect={100 * r['effect']:+.1f}% "
                  f"CI [{100 * r['ci'][0]:+.1f}, {100 * r['ci'][1]:+.1f}] placebo_p={r['placebo_p']:.3f} holm_p={r['holm_p']:.3f} mde={100 * (r['mde'] or 0):.1f}%")


if __name__ == "__main__":
    main()
