"""Parsing and validation of the raw Agmarknet portal exports.

Two export types are supported:

* **History** ("All Type of Report (All Grades)"): one row per market, crop and
  day with the arrivals-weighted modal price and total arrivals, 2021 onward.
  The portal appends footer rows ("Note: ...") and writes the date range into
  the column headers, so columns are assigned by position and footers dropped.
* **Daily** ("Daily Price Arrival Report"): one row per market, crop, variety
  and grade with min / max / modal price and arrivals, one year only.

Every row keeps a `source` tag. No row in this study is synthetic or imputed.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from gfmc.config import DAILY_GLOB, DATA_DIR, HISTORY_GLOB

HISTORY_COLUMNS = [
    "state", "district", "market", "group", "commodity",
    "date", "arrivals", "arrival_unit", "price", "price_unit",
]
EXPECTED_PRICE_UNIT = "Rs./Quintal"
EXPECTED_ARRIVAL_UNIT = "Metric Tonnes"
DATE_FORMAT = "%d-%m-%Y"


class DataError(ValueError):
    """Raised when an export does not have the layout the study depends on."""


@dataclass
class LoadReport:
    """What was read, what was dropped and why (for the paper's data section)."""

    source: str
    files: List[str] = field(default_factory=list)
    rows_read: int = 0
    footer_rows_dropped: int = 0
    unparseable_dates: int = 0
    nonpositive_price: int = 0
    nonpositive_arrivals: int = 0
    duplicate_keys: int = 0
    rows_kept: int = 0
    date_min: Optional[str] = None
    date_max: Optional[str] = None

    def as_dict(self) -> Dict:
        return self.__dict__.copy()


def _check_units(frame: pd.DataFrame, price_col: str, arrival_col: str) -> None:
    bad_p = set(frame[price_col].dropna().unique()) - {EXPECTED_PRICE_UNIT}
    bad_a = set(frame[arrival_col].dropna().unique()) - {EXPECTED_ARRIVAL_UNIT}
    if bad_p or bad_a:
        raise DataError(f"Unexpected units: price {sorted(bad_p)}, arrivals {sorted(bad_a)}")


def find_history_files(data_dir: Path = DATA_DIR) -> List[Path]:
    """Every market-level history export in the folder, oldest download first.

    A later, shorter export is an update, not a replacement, so all of them are read and layered
    (see `load_history`). A district-level download (no Market column) cannot feed the study and is skipped.
    """
    hits = [Path(p) for p in glob.glob(str(data_dir / HISTORY_GLOB))]
    if not hits:
        raise FileNotFoundError(f"No history export matching {HISTORY_GLOB} in {data_dir}")
    market_level = [p for p in hits if _header_width(p) == len(HISTORY_COLUMNS)]
    if not market_level:
        raise DataError(f"No market-level history export (with a Market column) among {[p.name for p in hits]}")
    return sorted(market_level, key=_export_time)  # by export time, not by name


def find_history_file(data_dir: Path = DATA_DIR) -> Path:
    """The newest market-level export (kept for callers that want a single file)."""
    return find_history_files(data_dir)[-1]


def _header_width(path: Path) -> int:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        fh.readline()
        return len(fh.readline().rstrip("\r\n").split(","))


def _export_time(path: Path):
    from datetime import datetime
    try:
        return datetime.strptime("_".join(path.stem.split("_")[-3:]), "%d-%m-%Y_%I-%M-%S_%p")
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime)


def _read_history_file(path: Path, rep: LoadReport) -> pd.DataFrame:
    """One export, cleaned; the counts are added to `rep`."""
    raw = pd.read_csv(path, skiprows=1, thousands=",", dtype=str, keep_default_na=False)
    if raw.shape[1] != len(HISTORY_COLUMNS):
        raise DataError(f"History export has {raw.shape[1]} columns, expected {len(HISTORY_COLUMNS)}")
    raw.columns = HISTORY_COLUMNS
    rep.rows_read += len(raw)

    dates = pd.to_datetime(raw["date"], format=DATE_FORMAT, errors="coerce")
    footer = dates.isna() & (raw["market"].str.strip() == "")
    rep.footer_rows_dropped += int(footer.sum())
    rep.unparseable_dates += int((dates.isna() & ~footer).sum())
    raw, dates = raw[dates.notna()].copy(), dates[dates.notna()]
    raw["date"] = dates.dt.normalize()

    for col in ("arrivals", "price"):
        raw[col] = pd.to_numeric(raw[col].str.replace(",", "", regex=False), errors="coerce")
    _check_units(raw, "price_unit", "arrival_unit")

    for col in ("state", "district", "market", "commodity"):
        raw[col] = raw[col].str.strip()

    rep.nonpositive_price += int((raw["price"] <= 0).sum())
    rep.nonpositive_arrivals += int((raw["arrivals"] <= 0).sum())
    raw = raw[(raw["price"] > 0) & raw["price"].notna()].copy()
    raw["arrivals"] = raw["arrivals"].where(raw["arrivals"] > 0)  # keep the price, drop the bad volume
    return raw[["date", "state", "district", "market", "commodity", "price", "arrivals"]]


def load_history(path: Optional[Path] = None, data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, LoadReport]:
    """Read the market-level history export(s) into a clean long frame.

    With no `path`, every market-level export in the data folder is read, oldest download first, and layered: where two
    exports hold the same market, crop and day the later download wins. `duplicate_keys` counts the keys resolved that way
    (within one file or across files).
    """
    paths = [Path(path)] if path else find_history_files(data_dir)
    rep = LoadReport(source="agmarknet_all_type_report", files=[p.name for p in paths])
    raw = pd.concat([_read_history_file(p, rep) for p in paths], ignore_index=True)

    rep.duplicate_keys = int(raw.duplicated(["date", "market", "commodity"]).sum())
    if rep.duplicate_keys:
        raw = raw.drop_duplicates(["date", "market", "commodity"], keep="last")  # later export wins

    out = raw.copy()
    out["source"] = rep.source
    out = out.sort_values(["commodity", "market", "date"]).reset_index(drop=True)
    rep.rows_kept = len(out)
    rep.date_min, rep.date_max = str(out["date"].min().date()), str(out["date"].max().date())
    return out, rep


def load_daily_reports(paths: Optional[List[Path]] = None, data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, LoadReport]:
    """Read the per-variety daily reports and aggregate to market-day.

    The modal price is the arrivals-weighted mean over varieties and grades,
    matching how the portal defines the market-level price in the history
    export (stated in that export's footer). Min and max are the extremes.
    """
    paths = [Path(p) for p in paths] if paths else sorted(Path(p) for p in glob.glob(str(data_dir / DAILY_GLOB)))
    if not paths:
        raise FileNotFoundError(f"No daily reports matching {DAILY_GLOB} in {data_dir}")
    rep = LoadReport(source="agmarknet_daily_report", files=[p.name for p in paths])

    frames = [pd.read_csv(p, skiprows=1, thousands=",") for p in paths]
    raw = pd.concat(frames, ignore_index=True)
    rep.rows_read = len(raw)
    need = {"Market", "Commodity", "Min Price", "Max Price", "Modal Price", "Arrival Quantity", "Arrival Date",
            "Price Unit", "Arrival Unit"}
    if need - set(raw.columns):
        raise DataError(f"Daily report missing columns: {sorted(need - set(raw.columns))}")
    _check_units(raw, "Price Unit", "Arrival Unit")

    raw["date"] = pd.to_datetime(raw["Arrival Date"], format=DATE_FORMAT, errors="coerce")
    rep.unparseable_dates = int(raw["date"].isna().sum())
    raw = raw.dropna(subset=["date"]).drop_duplicates()
    raw["arr"] = raw["Arrival Quantity"].fillna(0.0).clip(lower=0.0)
    raw["w"] = raw["Modal Price"] * raw["arr"]

    g = raw.groupby(["date", "Market", "Commodity"])
    out = g.agg(min_price=("Min Price", "min"), max_price=("Max Price", "max"), arrivals=("arr", "sum"),
                w=("w", "sum"), simple=("Modal Price", "mean"), varieties=("Modal Price", "size")).reset_index()
    out["price"] = np.where(out["arrivals"] > 0, out["w"] / out["arrivals"].where(out["arrivals"] > 0, 1.0), out["simple"])
    out["price"] = out["price"].clip(lower=out["min_price"], upper=out["max_price"])
    out = out.rename(columns={"Market": "market", "Commodity": "commodity"})
    out["arrivals"] = out["arrivals"].where(out["arrivals"] > 0)
    out["source"] = rep.source
    out = out[["date", "market", "commodity", "price", "min_price", "max_price", "arrivals", "varieties", "source"]]
    out = out.sort_values(["commodity", "market", "date"]).reset_index(drop=True)
    rep.rows_kept = len(out)
    rep.date_min, rep.date_max = str(out["date"].min().date()), str(out["date"].max().date())
    return out, rep


def crosscheck_sources(history: pd.DataFrame, daily: pd.DataFrame, commodity: str) -> Dict[str, float]:
    """Compare the two exports where they overlap (an integrity check on the data itself)."""
    a = history[history["commodity"] == commodity].set_index(["date", "market"])["price"]
    b = daily[daily["commodity"] == commodity].set_index(["date", "market"])["price"]
    both = pd.concat([a.rename("history"), b.rename("daily")], axis=1, join="inner").dropna()
    if both.empty:
        return {"overlap_rows": 0}
    rel = (both["history"] - both["daily"]).abs() / both["daily"]
    return {
        "overlap_rows": int(len(both)),
        "pearson_r": float(np.corrcoef(both["history"], both["daily"])[0, 1]),
        "median_abs_rel_diff": float(rel.median()),
        "share_within_5pct": float((rel <= 0.05).mean()),
    }
