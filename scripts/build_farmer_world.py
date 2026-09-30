"""
Build the farmer data world from the real Agmarknet downloads and publish its
forecasts.

    python scripts/build_farmer_world.py            # ingest + train + publish
    python scripts/build_farmer_world.py --ingest   # data only
    python scripts/build_farmer_world.py --train    # model only (data already built)

Inputs (copied into mandisense_ai/data/farmer/source/ so a build is
reproducible from the repository alone):

* the district "All Type of Report" download: one arrivals-weighted price per
  district, crop and day, Jan 2021 onward -- the long history the forecaster
  is trained on.
* the per-mandi "Daily Price Arrival Report" downloads: min / modal / max and
  arrivals per mandi, Nov 2025 onward -- what the farmer sees as today's
  price at each mandi, and what the fair-price check compares an offer to.

The two are kept in separate tables on purpose. Training on both would count
the same sales twice (a district price *is* an average of its mandis' prices).

Never reads or writes the trader's observation store, model bundle or
forecast store.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.farmer import registry, world  # noqa: E402
from mandisense_ai.forecasting.config import DEFAULT_CONFIG  # noqa: E402
from mandisense_ai.forecasting.store import ObservationStore  # noqa: E402
from mandisense_ai.forecasting.validation import validate_observations  # noqa: E402

DISTRICT_FILE_GLOB = "All_Type_of_Report*.csv"
MANDI_FILE_GLOB = "Daily Price Arrival Report*Karnataka*.csv"

# A district series is trained on only if it is dense enough to learn from and
# still printing. The forecaster's own gates (60 days of history, 21-day
# freshness, 10 contiguous prints) then decide what is actually published.
MIN_SERIES_SKILL = 0.01
MIN_SERIES_DIRECTION = 0.56
MIN_TRAIN_DAYS = 500
MAX_STALE_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stage_sources(district_csv: Path | None, mandi_dir: Path | None) -> None:
    world.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    if district_csv:
        shutil.copy2(district_csv, world.SOURCE_DIR / "district_report.csv")
    if mandi_dir:
        seen: set[str] = set()
        for path in sorted(glob.glob(str(mandi_dir / MANDI_FILE_GLOB))):
            digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
            if digest in seen:  # the download was saved twice
                continue
            seen.add(digest)
            shutil.copy2(path, world.SOURCE_DIR / f"mandi_report_{len(seen):02d}.csv")


def build_district_observations() -> dict:
    raw = pd.read_csv(world.SOURCE_DIR / "district_report.csv", skiprows=1, thousands=",")
    raw.columns = ["state", "district", "group", "commodity", "date", "arrivals", "arr_unit", "price", "price_unit"]
    raw = raw[raw["date"].notna() & raw["state"].notna()].copy()
    raw["date"] = pd.to_datetime(raw["date"], format="%d-%m-%Y", errors="coerce")
    raw = raw.dropna(subset=["date"])

    raw["district_id"] = raw["district"].map(registry.AGMARKNET_DISTRICT_TO_ID)
    raw["crop"] = raw["commodity"].map(registry.AGMARKNET_TO_CROP)
    known = raw.dropna(subset=["district_id", "crop"])
    if (known["price_unit"] != "Rs./Quintal").any() or (known["arr_unit"] != "Metric Tonnes").any():
        raise ValueError("Unexpected price or arrival unit in the district report")

    obs = pd.DataFrame({
        "date": known["date"].dt.normalize(),
        "commodity": known["crop"],
        "mandi_id": known["district_id"],
        "modal_price": known["price"].astype(float),
        "min_price": np.nan,
        "max_price": np.nan,
        "arrivals": known["arrivals"].astype(float),
        "state": "Karnataka",
        "district": known["district"],
        "source": "agmarknet_district_weighted",
        "ingested_at": _now(),
        "quality_score": 1.0,
        "quality_flags": "",
    })

    accepted, report = validate_observations(obs, history=None)
    rejected = len(obs) - len(accepted)

    # Only series dense and current enough to learn from are kept. The rest are
    # left out of the farmer world entirely, so the screens never offer a crop
    # and district the data cannot speak for.
    end = accepted["date"].max()
    stats = accepted.groupby(["commodity", "mandi_id"])["date"].agg(days="nunique", last="max")
    keep = stats[(stats["days"] >= MIN_TRAIN_DAYS) & ((end - stats["last"]).dt.days <= MAX_STALE_DAYS)]
    kept_keys = set(keep.index)
    mask = [(c, m) in kept_keys for c, m in zip(accepted["commodity"], accepted["mandi_id"])]
    final = accepted[mask].reset_index(drop=True)

    world.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if world.DISTRICT_OBSERVATIONS.exists():
        world.DISTRICT_OBSERVATIONS.unlink()
    counts = ObservationStore(world.DISTRICT_OBSERVATIONS).upsert(final)

    dropped = stats.drop(index=list(kept_keys))
    return {
        "rows_read": int(len(raw)),
        "rows_rejected_by_bounds_gate": int(rejected),
        "series_kept": len(kept_keys),
        "series_dropped_sparse_or_stale": [f"{c}/{m} ({int(r.days)}d)" for (c, m), r in dropped.iterrows()],
        "date_range": [str(final["date"].min().date()), str(final["date"].max().date())],
        **counts,
    }


def build_mandi_prices() -> dict:
    frames = [pd.read_csv(p, skiprows=1, thousands=",") for p in sorted(glob.glob(str(world.SOURCE_DIR / "mandi_report_*.csv")))]
    if not frames:
        return {"rows": 0}
    raw = pd.concat(frames, ignore_index=True).drop_duplicates()
    raw["date"] = pd.to_datetime(raw["Arrival Date"], format="%d-%m-%Y", errors="coerce")
    raw = raw.dropna(subset=["date"])
    raw["mandi_id"] = raw["Market"].str.strip().map(registry.AGMARKNET_MARKET_TO_ID)
    raw["crop"] = raw["Commodity"].map(registry.AGMARKNET_TO_CROP)
    raw = raw.dropna(subset=["mandi_id", "crop"]).copy()
    if (raw["Price Unit"] != "Rs./Quintal").any():
        raise ValueError("Unexpected price unit in a per-mandi report")

    raw["arr"] = raw["Arrival Quantity"].fillna(0.0)
    raw["w_modal"] = raw["Modal Price"] * raw["arr"]

    grouped = raw.groupby(["date", "crop", "mandi_id"])
    out = grouped.agg(
        min_price=("Min Price", "min"),
        max_price=("Max Price", "max"),
        arrivals=("arr", "sum"),
        w=("w_modal", "sum"),
        simple=("Modal Price", "mean"),
        varieties=("Variety", "nunique"),
    ).reset_index()
    # Arrivals-weighted across varieties and grades, matching how the district
    # report itself defines its price; plain mean where no volume was reported.
    out["modal_price"] = np.where(out["arrivals"] > 0, out["w"] / out["arrivals"].where(out["arrivals"] > 0, 1), out["simple"])
    out["modal_price"] = out["modal_price"].clip(lower=out["min_price"], upper=out["max_price"])
    out = out.rename(columns={"crop": "commodity"})
    out["district"] = out["mandi_id"].map(lambda m: registry.MANDIS[m].district)
    out = out[["date", "commodity", "mandi_id", "district", "min_price", "modal_price", "max_price", "arrivals", "varieties"]]
    out = out.sort_values(["commodity", "mandi_id", "date"]).reset_index(drop=True)
    out.to_parquet(world.MANDI_PRICES, index=False)
    per = out.groupby(["commodity", "mandi_id"]).size()
    return {"rows": int(len(out)), "series": int(len(per)), "date_range": [str(out["date"].min().date()), str(out["date"].max().date())]}



def build_model_report(obs: pd.DataFrame, bundle, prepared, config) -> dict:
    """Out-of-sample accuracy in the terms a farmer cares about, from the same
    expanding-window folds the model was promoted on.

    Every number is measured on rows the model was not trained on. The
    per-crop breakdown refits the model fold by fold exactly as the promotion
    test does, so it can be compared with the headline skill without a second,
    differently-built evaluation.
    """
    from mandisense_ai.forecasting.train import _apply_arrival_dropout, _make_estimator, _sample_weights

    frame, features = prepared
    rows = []
    for horizon in bundle.promoted_horizons:
        target = f"y_h{horizon}"
        usable = frame[frame[target].notna()].sort_values("date").reset_index(drop=True)
        cuts = [usable["date"].quantile(q) for q in np.linspace(0.5, 1.0, config.walk_forward_folds + 1)]
        for i in range(config.walk_forward_folds):
            train = usable[usable["date"] <= cuts[i]]
            valid = usable[(usable["date"] > cuts[i]) & (usable["date"] <= cuts[i + 1])]
            if len(train) < config.min_train_rows or len(valid) < 20:
                continue
            fit = _apply_arrival_dropout(train, features, config, seed=config.random_seed + horizon * 100 + i)
            model = _make_estimator(config)
            model.fit(fit[features], fit[target], sample_weight=_sample_weights(fit, config), verbose=False)
            rows.append(pd.DataFrame({
                "horizon": horizon, "fold": i + 1, "date": valid["date"].to_numpy(),
                "commodity": valid["commodity"].to_numpy(), "place": valid["mandi_id"].to_numpy(),
                "actual": valid[target].to_numpy(), "pred": model.predict(valid[features]),
            }))
    oos = pd.concat(rows, ignore_index=True)
    oos["abs_model"] = (oos["actual"] - oos["pred"]).abs()
    oos["abs_naive"] = oos["actual"].abs()

    def summarise(g: pd.DataFrame) -> dict:
        moved = g[g["actual"].abs() > 0.005]
        return {
            "forecasts": int(len(g)),
            "skill_vs_no_change": round(float(1 - g["abs_model"].mean() / g["abs_naive"].mean()), 4),
            "direction_right": round(float(((moved["pred"] > 0) == (moved["actual"] > 0)).mean()), 4) if len(moved) else None,
            "base_rate_price_fell": round(float((g["actual"] < 0).mean()), 4),
        }

    horizons = {}
    for h in config.horizons:
        g = oos[oos["horizon"] == h]
        entry = {"promoted": h in bundle.promoted_horizons,
                 "skill_vs_no_change": bundle.validation.get(str(h), {}).get("skill") if str(h) in bundle.validation else bundle.validation.get(h, {}).get("skill")}
        if len(g):
            entry.update(summarise(g))
        q = bundle.quantile_backtest.get("horizons", {}).get(str(h), {})
        entry["coverage_90"] = q.get("coverage_90")
        entry["mean_band_width_pct"] = q.get("mean_band_width_pct")
        d = bundle.decision_backtest.get("horizons", {}).get(str(h), {})
        chosen = d.get("chosen_threshold")
        pick = next((t for t in d.get("thresholds", []) if t.get("threshold") == chosen), None)
        if pick:
            entry["decision"] = {k: pick.get(k) for k in ("threshold", "precision_sell", "precision_hold", "coverage", "sell_calls", "hold_calls")}
        horizons[str(h)] = entry

    served = oos[oos["horizon"].isin(bundle.promoted_horizons)]
    last_fold = served[served["fold"] == served["fold"].max()]
    by_crop = {c: summarise(g) for c, g in served.groupby("commodity")}
    by_place = {c: summarise(g) for c, g in served.groupby("place")}
    recent = {c: summarise(g) for c, g in last_fold.groupby("commodity")}

    # A call (sell / hold) is only offered for a crop and district whose
    # out-of-sample record earns it: it beat "no change" by the same margin the
    # model itself had to clear, and read the direction right clearly more
    # often than a coin. Everywhere else the app shows the price and range and
    # says plainly that it has no dependable call.
    series_quality = {}
    for (crop, place), g in served.groupby(["commodity", "place"]):
        stats = summarise(g)
        recent_g = last_fold[(last_fold["commodity"] == crop) & (last_fold["place"] == place)]
        stats["skill_latest_fold"] = summarise(recent_g)["skill_vs_no_change"] if len(recent_g) >= 30 else None
        stats["serves_call"] = bool(
            stats["forecasts"] >= 300
            and stats["skill_vs_no_change"] >= MIN_SERIES_SKILL
            and (stats["direction_right"] or 0) >= MIN_SERIES_DIRECTION
            and (stats["skill_latest_fold"] is None or stats["skill_latest_fold"] > 0)
        )
        series_quality[f"{crop}/{place}"] = stats

    return {
        "generated_at": _now(),
        "data": {
            "source": "Agmarknet district reports (arrivals-weighted)",
            "series": int(obs.groupby(["commodity", "mandi_id"]).ngroups),
            "rows": int(len(obs)),
            "from": str(obs["date"].min().date()),
            "to": str(obs["date"].max().date()),
        },
        "method": "Expanding-window walk-forward, 4 folds; every figure is on rows the model had not seen.",
        "served_horizons": [int(h) for h in bundle.promoted_horizons],
        "overall": summarise(served),
        "last_fold_window": [str(last_fold["date"].min().date()), str(last_fold["date"].max().date())] if len(last_fold) else None,
        "horizons": horizons,
        "by_crop": by_crop,
        "by_crop_latest_fold": recent,
        "by_district": by_place,
        "series_quality": series_quality,
        "call_rule": {"min_skill": MIN_SERIES_SKILL, "min_direction_right": MIN_SERIES_DIRECTION,
                      "also_required": "not worse than no-change in the most recent test window"},
    }


def rebuild_report() -> dict:
    from mandisense_ai.forecasting.train import ForecastBundle, _prepare_training_frame

    obs = ObservationStore(world.DISTRICT_OBSERVATIONS).read()
    bundle = ForecastBundle.load(world.BUNDLE_DIR)
    report = build_model_report(obs, bundle, _prepare_training_frame(obs, DEFAULT_CONFIG), DEFAULT_CONFIG)
    world.MODEL_REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return {k: v for k, v in report["series_quality"].items()}


def train_and_publish() -> dict:
    from mandisense_ai.forecasting.backtest import run_backtest
    from mandisense_ai.forecasting.batch_predict import generate_forecasts
    from mandisense_ai.forecasting.decision import run_decision_backtest
    from mandisense_ai.forecasting.quantile import run_quantile_backtest
    from mandisense_ai.forecasting.train import _prepare_training_frame, train_bundle

    obs = ObservationStore(world.DISTRICT_OBSERVATIONS).read()
    config = DEFAULT_CONFIG
    prepared = _prepare_training_frame(obs, config)
    bundle = train_bundle(obs, config, prepared=prepared)
    bundle.backtest = run_backtest(obs, config, prepared=prepared)
    bundle.quantile_backtest = run_quantile_backtest(obs, config, prepared=prepared)
    bundle.quantile_promoted_horizons = [
        int(h) for h, r in bundle.quantile_backtest.get("horizons", {}).items() if r.get("calibration") == "CALIBRATED"
    ]
    bundle.decision_backtest = run_decision_backtest(obs, config, prepared=prepared)
    bundle.decision_thresholds = {int(h): t for h, t in bundle.decision_backtest.get("chosen_thresholds", {}).items()}
    world.BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    bundle.save(world.BUNDLE_DIR)

    world.MODEL_REPORT.write_text(json.dumps(build_model_report(obs, bundle, prepared, config), indent=2, default=str), encoding="utf-8")

    store = generate_forecasts(obs, bundle, config)
    store.save(world.FORECAST_STORE)
    if world.LEDGER.exists():
        world.LEDGER.unlink()
    try:
        world.ledger().record_publication(store)
    except Exception as exc:  # the ledger is monitoring; it must not fail a publish
        print("ledger skipped:", exc)

    return {
        "training_rows": bundle.training_rows,
        "promoted_horizons": bundle.promoted_horizons,
        "skill": {str(h): v.get("skill") for h, v in bundle.validation.items()},
        "fold_win_rate": {str(h): v.get("fold_win_rate") for h, v in bundle.validation.items()},
        "coverage_90": {str(h): r.get("coverage_90") for h, r in bundle.quantile_backtest.get("horizons", {}).items()},
        "decision_thresholds": bundle.decision_thresholds,
        "series_forecast": store.diagnostics.get("series_forecast"),
        "series_skipped": store.diagnostics.get("series_skipped"),
        "as_of": store.as_of_date,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--report", action="store_true", help="rebuild only the accuracy report from the saved bundle")
    parser.add_argument("--district-csv", type=Path)
    parser.add_argument("--mandi-dir", type=Path)
    args = parser.parse_args()
    do_all = not (args.ingest or args.train or args.report)

    if args.district_csv or args.mandi_dir:
        stage_sources(args.district_csv, args.mandi_dir)
    if do_all or args.ingest:
        print(json.dumps({"district": build_district_observations(), "mandi": build_mandi_prices()}, indent=2, default=str))
    if do_all or args.train:
        print(json.dumps(train_and_publish(), indent=2, default=str))
    if args.report:
        print(json.dumps(rebuild_report(), indent=1, default=str))


if __name__ == "__main__":
    main()
