"""
Run the nested walk-forward experiments and their analysis for every studied crop, then the tomato-only audits.

    python research/scripts/run_all_crops.py               # everything (hours; tomato dominates)
    python research/scripts/run_all_crops.py --crops Ginger # one crop

Tomato carries the full specification set (the paper's main study); the secondary crops (onion, potato, ginger) run the five specifications that
answer the headline questions (random walk, observed-label and realised-label LightGBM, realised-label neural with MSE and with SPO+), which
takes minutes per crop. Garlic is not run: only one mandi has enough reported days, so there is no market choice to learn
(see `gfmc/config.py`).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECONDARY_SPECS = "rw,lgbm_obs,lgbm_filled,ds_mse_filled,ds_spo"


def run(*args: str) -> int:
    cmd = [sys.executable, *args]
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=HERE.parent).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crops", nargs="*", default=["Tomato", "Onion", "Potato", "Ginger"])
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--skip-audits", action="store_true", help="skip the tomato leakage, foundation-model and silence studies")
    a = ap.parse_args()
    failed = []
    for crop in a.crops:
        extra = [] if crop == "Tomato" else ["--specs", SECONDARY_SPECS]
        if run("scripts/run_experiments.py", "--crop", crop, "--jobs", str(a.jobs), *extra) or run("scripts/analyze.py", "--crop", crop):
            failed.append(crop)
    if not a.skip_audits and "Tomato" in a.crops:
        for script in ("run_leakage.py", "run_foundation.py", "run_silence.py"):
            if run(f"scripts/{script}"):
                failed.append(script)
    print("FAILED:" if failed else "all done", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
