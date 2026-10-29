"""Contribution 3: is market silence informative?  (reporting and returns tests)

    python scripts/run_silence.py [--crop Tomato]
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from gfmc import silence  # noqa: E402
from gfmc.config import RESULTS_DIR  # noqa: E402
from gfmc.data import loader, panel  # noqa: E402
from gfmc.dataset import build_decision_data  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="Tomato")
    ap.add_argument("--perms", type=int, default=30)
    a = ap.parse_args()
    hist, _ = loader.load_history()
    dd = build_decision_data(panel.build_panel(hist, a.crop))
    out = RESULTS_DIR / a.crop.lower() / "silence"
    out.mkdir(parents=True, exist_ok=True)

    A = silence.reporting_test(dd, perms=a.perms)
    A["per_fold_horizon"].to_csv(out / "reporting_per_fold_horizon.csv", index=False)
    B = silence.returns_test(dd)
    B["per_fold"].to_csv(out / "returns_per_fold.csv", index=False)
    (out / "summary.json").write_text(json.dumps({"reporting": A["pooled"], "returns_dm": B["dm_silence_vs_base"]},
                                                 indent=2), encoding="utf-8")
    print("REPORTING (A):", json.dumps(A["pooled"], indent=2))
    print(A["per_fold_horizon"].groupby("fold")[["auc_base", "auc_silence", "d_auc"]].mean().round(4))
    print("RETURNS (B):", json.dumps(B["dm_silence_vs_base"], indent=2))
    print(B["per_fold"].round(5).to_string(index=False))


if __name__ == "__main__":
    main()
