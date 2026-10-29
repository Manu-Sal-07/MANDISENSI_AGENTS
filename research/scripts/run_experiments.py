"""Train, tune and predict every (model, outer fold) in parallel. Resumable.

    python scripts/run_experiments.py [--crop Tomato] [--jobs 16] [--trials-nn 20] [--trials-gbm 25]
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from joblib import Parallel, delayed  # noqa: E402

from gfmc.config import OUTER_FOLDS  # noqa: E402
from gfmc.experiment import run_task  # noqa: E402
from gfmc.specs import SPECS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="Tomato")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--trials-nn", type=int, default=20)
    ap.add_argument("--trials-gbm", type=int, default=25)
    ap.add_argument("--specs", default="", help="comma-separated subset")
    ap.add_argument("--folds", default="", help="comma-separated subset, e.g. 0,1")
    a = ap.parse_args()

    names = [s for s in a.specs.split(",") if s] or [s.name for s in SPECS]
    folds = [int(f) for f in a.folds.split(",") if f] or list(range(len(OUTER_FOLDS)))
    heavy = {s.name: (s.family == "deepsets") for s in SPECS}
    trials = {s.name: (a.trials_nn if s.family == "deepsets" else a.trials_gbm) for s in SPECS}
    tasks = sorted(((n, f) for n in names for f in folds), key=lambda t: (not heavy[t[0]], t[1]))
    print(f"{len(tasks)} tasks, {a.jobs} workers", flush=True)

    t0 = time.time()
    results = Parallel(n_jobs=a.jobs, verbose=10, backend="loky")(
        delayed(run_task)(n, f, a.crop, trials[n], 3 if heavy[n] else 1) for n, f in tasks)
    done = [r for r in results if r]
    print(f"finished {len(done)} tasks in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
