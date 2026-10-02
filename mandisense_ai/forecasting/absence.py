"""
Informative missingness for sparse mandi panels.

A day with no print is currently treated as nothing at all: the observation
store drops rows without a usable price, the feature layer carries a single
``days_since_prev`` scalar, and the legacy data service forward-fills across
gaps. All three treat absence as a nuisance to be smoothed away.

In a mandi panel absence is not one thing and it is not noise. At least three
distinct events produce an identical hole in the series:

* the market traded, but **not this commodity** — nobody brought tomatoes;
* the market **did not open** — a holiday, a strike, a flood;
* the market opened and traded, but the **report never reached the feed**.

The first is a supply signal and belongs in the model. The third is a data
artifact and should, if anything, lower confidence. Collapsing them into one
"missing" is how a genuine scarcity signal gets thrown away.

Nothing in a single series can separate them — but the *panel* can, and the
panel is already held. On any given date:

* if other commodities printed at this mandi, the mandi was open, so this
  commodity's absence is a real ``NO_TRADE``;
* if this mandi printed nothing while the same commodity printed at many peer
  mandis, the silence is local to the market — ``MANDI_SILENT``;
* if almost nothing printed anywhere, the day itself is missing —
  ``MARKET_WIDE``, a calendar or feed artifact carrying no market information.

That cross-sibling / cross-peer identification is the whole idea. It needs no
holiday calendar, no external data, and no assumption that missingness is at
random — which, in this feed, it plainly is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

ABSENCE_NO_TRADE = "NO_TRADE"
ABSENCE_MANDI_SILENT = "MANDI_SILENT"
ABSENCE_MARKET_WIDE = "MARKET_WIDE"

ABSENCE_FEATURE_COLUMNS = [
    "no_trade_30",
    "mandi_silent_30",
    "prev_gap_no_trade",
    "report_rate_90",
]


@dataclass(frozen=True)
class AbsenceConfig:
    """Tunables for absence classification."""

    market_wide_fraction: float = 0.5
    """A date whose total print count falls to this fraction of the panel's
    typical (median) daily total, or below, is treated as a market-wide
    outage rather than a set of independent local absences.

    Deliberately a fraction of the *typical* day rather than a quantile of
    the whole distribution: in a panel that is normally near-complete, all
    but a handful of days sit at (or near) the maximum possible count, so a
    low quantile of that distribution sits at the maximum too — a single
    ordinary absence would then look identical to a real market-wide outage.
    Comparing each day against the median sidesteps that; a day has to lose
    roughly half its expected prints before it is treated as calendar-wide
    rather than as one or two local, attributable absences."""

    peer_quorum: int = 3
    """Peer mandis that must have printed the same commodity before a local
    silence can be attributed to the mandi rather than to the feed."""

    lookback_days: int = 30
    """Window over which absence counts are accumulated into features."""

    report_rate_window: int = 90

    min_series_rows: int = 30
    """Series shorter than this have no stable notion of an expected trading
    day, so absences within them are not classified."""


DEFAULT_ABSENCE_CONFIG = AbsenceConfig()


def _normalise(observations: pd.DataFrame) -> pd.DataFrame:
    frame = observations[["date", "commodity", "mandi_id"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    return frame.dropna(subset=["date"]).drop_duplicates()


def classify_absences(
    observations: pd.DataFrame,
    config: AbsenceConfig = DEFAULT_ABSENCE_CONFIG,
) -> pd.DataFrame:
    """
    Label every absent day inside each series' active span.

    Returns a long frame of ``(commodity, mandi_id, date, absence_type)``.
    Days outside a series' first/last observation are not absences — the
    series simply did not exist yet, or has ended.
    """
    if observations is None or observations.empty:
        return pd.DataFrame(columns=["commodity", "mandi_id", "date", "absence_type"])

    present = _normalise(observations)
    if present.empty:
        return pd.DataFrame(columns=["commodity", "mandi_id", "date", "absence_type"])

    # Mandis that printed anything at all on a date.
    mandi_open: Dict[pd.Timestamp, Set[str]] = {
        date: set(group["mandi_id"])
        for date, group in present.groupby("date", sort=False)
    }

    # How many mandis printed each commodity on each date.
    commodity_day_counts: Dict[Tuple[str, pd.Timestamp], int] = (
        present.groupby(["commodity", "date"]).size().to_dict()
    )

    daily_totals = present.groupby("date").size()
    typical_total = float(daily_totals.median())
    market_wide_threshold = typical_total * config.market_wide_fraction
    thin_days: Set[pd.Timestamp] = set(
        daily_totals[daily_totals <= market_wide_threshold].index
    )

    records: List[Dict[str, object]] = []

    for (commodity, mandi_id), group in present.groupby(["commodity", "mandi_id"], sort=False):
        if len(group) < config.min_series_rows:
            continue

        dates = set(group["date"])
        span = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
        missing = [day for day in span if day not in dates]
        if not missing:
            continue

        for day in missing:
            if day in thin_days:
                absence_type = ABSENCE_MARKET_WIDE
            elif mandi_id in mandi_open.get(day, ()):
                # The mandi transacted that day; this commodity did not show up.
                absence_type = ABSENCE_NO_TRADE
            elif commodity_day_counts.get((commodity, day), 0) >= config.peer_quorum:
                absence_type = ABSENCE_MANDI_SILENT
            else:
                absence_type = ABSENCE_MARKET_WIDE

            records.append(
                {
                    "commodity": commodity,
                    "mandi_id": mandi_id,
                    "date": day,
                    "absence_type": absence_type,
                }
            )

    frame = pd.DataFrame.from_records(
        records, columns=["commodity", "mandi_id", "date", "absence_type"]
    )
    if not frame.empty:
        counts = frame["absence_type"].value_counts().to_dict()
        logger.info("Absence classification: %d absent days %s", len(frame), counts)
    return frame


def summarise(absences: pd.DataFrame) -> Dict[str, object]:
    """Panel-level absence composition, for the run record."""
    if absences is None or absences.empty:
        return {"total": 0, "by_type": {}}
    return {
        "total": int(len(absences)),
        "by_type": {str(k): int(v) for k, v in absences["absence_type"].value_counts().items()},
        "series_affected": int(absences.groupby(["commodity", "mandi_id"]).ngroups),
    }


def build_absence_features(
    observations: pd.DataFrame,
    absences: Optional[pd.DataFrame] = None,
    config: AbsenceConfig = DEFAULT_ABSENCE_CONFIG,
) -> pd.DataFrame:
    """
    Attach absence features to each observation.

    Every feature describes the window *ending the day before* the row, so no
    value here can encode anything the market had not already revealed.

    ``no_trade_30``
        Days in the trailing window when this mandi was open and this
        commodity did not trade. Rising values mean produce is not arriving,
        which is a supply signal the price series alone does not carry.

    ``mandi_silent_30``
        Days the mandi itself went quiet while peers traded. A data-reliability
        indicator rather than a market one.

    ``prev_gap_no_trade``
        Whether the gap immediately before this print was a genuine no-trade
        rather than a reporting artifact.

    ``report_rate_90``
        Share of days in the trailing window on which the series printed at
        all, which is what makes the two counts above comparable between a
        daily market and a twice-weekly one.
    """
    if observations is None or observations.empty:
        return observations

    frame = observations.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    if absences is None:
        absences = classify_absences(frame, config)

    for column in ABSENCE_FEATURE_COLUMNS:
        frame[column] = 0.0

    if absences is None or absences.empty:
        frame["report_rate_90"] = 1.0
        return frame

    absence_index: Dict[Tuple[str, str], pd.DataFrame] = {
        key: group.sort_values("date")
        for key, group in absences.groupby(["commodity", "mandi_id"], sort=False)
    }

    window = pd.Timedelta(days=config.lookback_days)
    rate_window = pd.Timedelta(days=config.report_rate_window)

    pieces: List[pd.DataFrame] = []
    for key, group in frame.groupby(["commodity", "mandi_id"], sort=False):
        group = group.sort_values("date").copy()
        series_absences = absence_index.get(key)

        if series_absences is None or series_absences.empty:
            group["report_rate_90"] = 1.0
            pieces.append(group)
            continue

        absence_dates = series_absences["date"].to_numpy()
        absence_types = series_absences["absence_type"].to_numpy()
        no_trade_dates = absence_dates[absence_types == ABSENCE_NO_TRADE]
        silent_dates = absence_dates[absence_types == ABSENCE_MANDI_SILENT]

        observed = group["date"].to_numpy()
        no_trade_counts = np.empty(len(group), dtype="float64")
        silent_counts = np.empty(len(group), dtype="float64")
        prev_no_trade = np.zeros(len(group), dtype="float64")
        report_rate = np.empty(len(group), dtype="float64")

        previous_observation: Optional[np.datetime64] = None
        for position, current in enumerate(observed):
            lower = current - window
            no_trade_counts[position] = np.sum(
                (no_trade_dates >= lower) & (no_trade_dates < current)
            )
            silent_counts[position] = np.sum(
                (silent_dates >= lower) & (silent_dates < current)
            )

            rate_lower = current - rate_window
            observed_in_window = np.sum((observed >= rate_lower) & (observed < current))
            absent_in_window = np.sum(
                (absence_dates >= rate_lower) & (absence_dates < current)
            )
            total = observed_in_window + absent_in_window
            report_rate[position] = (observed_in_window / total) if total > 0 else 1.0

            if previous_observation is not None:
                gap_absences = no_trade_dates[
                    (no_trade_dates > previous_observation) & (no_trade_dates < current)
                ]
                prev_no_trade[position] = 1.0 if gap_absences.size else 0.0
            previous_observation = current

        group["no_trade_30"] = no_trade_counts
        group["mandi_silent_30"] = silent_counts
        group["prev_gap_no_trade"] = prev_no_trade
        group["report_rate_90"] = report_rate
        pieces.append(group)

    result = pd.concat(pieces, ignore_index=True)
    return result.sort_values(["commodity", "mandi_id", "date"]).reset_index(drop=True)
