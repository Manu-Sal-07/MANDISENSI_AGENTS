"""Zero-shot time-series foundation model baseline on the leakage-benchmark origins.

Chronos-Bolt sees only the price history up to the origin (nothing is trained
on this data) and forecasts the log price h days ahead; it is scored on exactly
the same (market, origin, horizon) targets as the decomposition hybrids.

    python scripts/run_foundation.py [--crop Tomato] [--model amazon/chronos-bolt-small]
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
import torch  # noqa: E402

from gfmc import stats  # noqa: E402
from gfmc.config import RESULTS_DIR  # noqa: E402
from gfmc.data import loader, panel  # noqa: E402

CONTEXT = 512


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="Tomato")
    ap.add_argument("--model", default="amazon/chronos-bolt-small")
    a = ap.parse_args()
    torch.set_num_threads(4)

    out = RESULTS_DIR / a.crop.lower() / "leakage"
    errs = pd.read_csv(out / "per_origin_errors.csv", parse_dates=["date"])
    hist, _ = loader.load_history()
    pan = panel.build_panel(hist, a.crop)

    from chronos import BaseChronosPipeline

    pipe = BaseChronosPipeline.from_pretrained(a.model, device_map="cpu", torch_dtype=torch.float32)
    t0 = time.time()
    rows = []
    keys = errs[["market", "date", "h"]].drop_duplicates()
    for market, g in keys.groupby("market"):
        j = pan.markets.index(market)
        y = pd.Series(pan.price[:, j]).ffill().to_numpy()
        logy = np.log(y)
        day_idx = {d: i for i, d in enumerate(pan.dates)}
        for h, gh in g.groupby("h"):
            ctxs = [torch.tensor(logy[max(0, day_idx[d] - CONTEXT + 1): day_idx[d] + 1], dtype=torch.float32)
                    for d in gh["date"]]
            preds = []
            for i in range(0, len(ctxs), 64):
                q, _ = pipe.predict_quantiles(inputs=ctxs[i:i + 64], prediction_length=int(h), quantile_levels=[0.5])
                preds.append(q[:, -1, 0].numpy())
            pred = np.concatenate(preds)
            base = np.array([logy[day_idx[d]] for d in gh["date"]])
            for d, p, b in zip(gh["date"], pred, base):
                rows.append({"market": market, "date": d, "h": int(h), "foundation": float(p - b)})
    fm = pd.DataFrame(rows)
    df = errs.merge(fm, on=["market", "date", "h"], how="left")
    df.to_csv(out / "per_origin_errors_with_foundation.csv", index=False)

    res = []
    for h, g in df.drop_duplicates(["market", "date", "h"]).groupby("h"):
        rw = np.abs(g["truth"]).to_numpy()
        e_f = np.abs(g["foundation"] - g["truth"]).to_numpy()
        res.append({"h": h, "n": len(g), "skill_foundation": 1 - e_f.mean() / rw.mean(), "model": a.model})
    res = pd.DataFrame(res)
    # paired comparison with the best-causal and with the published-protocol hybrids
    comp = []
    for (dec, fc, h), g in df.groupby(["decomposer", "forecaster", "h"]):
        ef = np.abs(g["foundation"] - g["truth"]).to_numpy()
        for proto in ("causal_joint", "published_joint", "published", "raw"):
            e = np.abs(g[proto] - g["truth"]).to_numpy()
            r = stats.paired_report(ef, e, seed=int(h))
            comp.append({"decomposer": dec, "forecaster": fc, "h": h, "vs": proto,
                         "foundation_minus_other_mae": r["mean_diff"], "p": r["p"]})
    res.to_csv(out / "foundation_skill.csv", index=False)
    pd.DataFrame(comp).to_csv(out / "foundation_vs_hybrids.csv", index=False)
    print(res.round(4).to_string(index=False))
    print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
