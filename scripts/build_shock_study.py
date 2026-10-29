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
DOC = PROJECT_ROOT / "docs" / "SHOCK_STUDY.md"


def write_report(artifact: dict) -> None:
    """The study as a readable document, generated from the artefact so the two cannot disagree."""
    own, cc = artifact["own_crop"], (artifact.get("cross_commodity") or {})
    rules = own["rules"]
    L = ["# Supply-shock study", "",
         f"Generated {artifact['generated_at'][:19]}Z from {artifact['data']['from']} to {artifact['data']['to']}; crops {', '.join(artifact['data']['crops'])}; "
         f"districts {', '.join(artifact['data']['districts'])}.", "",
         "A **shock onset** is a day when arrivals sit at least "
         f"{rules['z_onset']} standard deviations from their trailing norm in a district, with at least {rules['min_gap_days']} days since the previous onset. "
         "The **effect** is the crop's own price change over the horizon minus the average change of the other crops in the same district on the same dates, "
         "so market-wide moves cancel. Intervals are block bootstraps over weeks; the **placebo** moves every district's shocks to random other dates "
         f"({rules['placebo_draws']} draws, shifts of at least {rules['placebo_min_shift_days']} days) and asks how often a gap this large appears by chance; "
         f"**Holm** correction is applied across all {rules['holm_over']} tests. **Detectable** is the smallest effect each test could have found (2.8 standard errors).", "",
         "A result is **ROBUST** only if it survives Holm correction, the placebo, an interval that excludes zero and agreement across districts. "
         "**SUGGESTIVE** means it shows in the sample but fails one of those. Farmers are only ever shown robust results.", "",
         f"## Own-crop price response ({own['n_tested']} tests: {own['n_robust']} robust, {own['n_suggestive']} suggestive)", "",
         "| Crop | Shock | Days after | Episodes | Effect | 95% interval | Detectable | Placebo p | Holm p | Evidence |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in own["results"]:
        if r["status"] != "OK":
            L.append(f"| {r['crop']} | {r['direction']} | {r['horizon']} | {r.get('n', 0)} | not enough episodes | | | | | |")
            continue
        L.append(f"| {r['crop']} | {r['direction']} | {r['horizon']} | {r['n']} | {100 * r['effect']:+.1f}% | {100 * r['ci'][0]:+.1f} to {100 * r['ci'][1]:+.1f} | "
                 f"±{100 * (r['mde'] or 0):.1f}% | {r['placebo_p']:.3f} | {r['holm_p']:.3f} | {r['tier'].lower()} |")
    edges = [e for e in cc.get("edges", []) if e.get("status") == "OK"]
    if edges:
        L += ["", f"## Cross-commodity links ({len(edges)} tested)", "",
              "| When | Then | Episodes | Effect | 95% interval | Detectable | Placebo p | Published as |", "|---|---|---|---|---|---|---|---|"]
        for e in sorted(edges, key=lambda x: (not x.get("published"), -abs(x.get("effect") or 0))):
            L.append(f"| {e['source']} {e['shock']} | {e['target']} price | {e['n_episodes']} | {100 * e['effect']:+.1f}% | "
                     f"{100 * e['ci'][0]:+.1f} to {100 * e['ci'][1]:+.1f} | ±{100 * (e.get('min_detectable_effect') or 0):.1f}% | {e['placebo_p']:.3f} | "
                     f"{'robust' if e.get('published') else 'not published'} |")
    L += ["", "## Reading", "",
          "No own-crop price response is robust, so the application makes no claim that a glut or squeeze of arrivals will move a price. Where results are only suggestive "
          "they are shown to traders as leads to check, never as signals, and never to farmers. The farmer app reports only what is observed: arrivals against normal and the "
          "price gap to neighbouring districts.", "",
          "## Limits", "",
          "- Five crops in five districts over under six years give a few hundred episodes at best; the *detectable* column says how large an effect would have to be to be seen.",
          "- Thirty-plus tests invite chance findings; the Holm column is the guard, and the suggestive rows should be read with it.",
          "- Reported modal prices change in steps, so short-horizon price changes are lumpy and many are exactly zero."]
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text("\n".join(L), encoding="utf-8")


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
    write_report(artifact)
    print(f"wrote {OUT.name} in {time.time() - t0:.0f}s: tested {study['n_tested']}, robust {study['n_robust']}, suggestive {study['n_suggestive']}")
    for r in study["results"]:
        if r["status"] == "OK" and r["tier"] != "NONE":
            print(f"  {r['tier']:10s} {r['crop']:7s} {r['direction']:7s} h={r['horizon']:2d}d n={r['n']:3d} effect={100 * r['effect']:+.1f}% "
                  f"CI [{100 * r['ci'][0]:+.1f}, {100 * r['ci'][1]:+.1f}] placebo_p={r['placebo_p']:.3f} holm_p={r['holm_p']:.3f} mde={100 * (r['mde'] or 0):.1f}%")


if __name__ == "__main__":
    main()
