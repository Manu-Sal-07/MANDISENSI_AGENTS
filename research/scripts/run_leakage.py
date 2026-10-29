"""Contribution 1: published vs deployment-faithful decomposition-hybrid evaluation.

    python scripts/run_leakage.py [--crop Tomato] [--markets 5] [--step 3] [--jobs 12]
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from gfmc import leakage  # noqa: E402
from gfmc.config import RESULTS_DIR  # noqa: E402
from gfmc.data import loader, panel  # noqa: E402


def one(y, observed, dates, market, dec, fc, step):
    df = leakage.run_series(y, observed, dates, dec, fc, hs=(1, 7), step=step)
    df["market"] = market
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="Tomato")
    ap.add_argument("--markets", type=int, default=5)
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()

    hist, _ = loader.load_history()
    pan = panel.build_panel(hist, a.crop)
    top = list(pan.summary().sort_values("reported_days", ascending=False)["market"][: a.markets])
    out = RESULTS_DIR / a.crop.lower() / "leakage"
    out.mkdir(parents=True, exist_ok=True)

    series = {}
    for m in top:
        j = pan.markets.index(m)
        fp = pd.Series(pan.price[:, j]).ffill()
        first = fp.first_valid_index()
        series[m] = (np.log(fp.to_numpy()[first:]), pan.mask[first:, j], pan.dates[first:])

    tasks = [(m, dec, fc) for m in top for dec in ("STL", "VMD") for fc in ("ridge", "lgbm")]
    t0 = time.time()
    frames = Parallel(n_jobs=a.jobs, verbose=5)(
        delayed(one)(*series[m], m, dec, fc, a.step) for m, dec, fc in tasks)
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(out / "per_origin_errors.csv", index=False)

    summ = leakage.summarise(df)
    summ.to_csv(out / "summary.csv", index=False)
    per_market = []
    for m in top:
        s = leakage.summarise(df[df["market"] == m])
        s.insert(0, "market", m)
        per_market.append(s)
    pd.concat(per_market).to_csv(out / "summary_by_market.csv", index=False)

    m0 = top[0]
    y0, _, d0 = series[m0]
    sens = pd.DataFrame([leakage.sensitivity_table(y0, d0, d) for d in ("STL", "VMD")])
    sens.to_csv(out / "future_sensitivity.csv", index=False)
    print(summ.round(4).to_string(index=False))
    print(sens.to_string(index=False))
    print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
