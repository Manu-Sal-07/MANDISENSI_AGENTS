"""
Graded observation quality scoring.

The gate this replaces was binary and, measured against every run in the
ingestion log, never fired once: 898 records received, 0 rejected. Two design
choices made it inert.

**A single global spike threshold.** `|log(price / recent_median)| > 2.5`
means a print must move roughly twelvefold to be questioned. Tomato in Kolar
and potato in Agra do not share a volatility scale, so one constant is either
too loose for the stable series or too tight for the volatile one. Here the
comparison is scaled by *each series' own* dispersion of log returns, so the
same statistical surprise is treated the same way everywhere.

**Accept/reject with nothing in between.** A price can be mildly implausible
without being impossible, and throwing it away costs more information than it
saves. Every record now carries a continuous ``quality_score`` in [0, 1] that
survives into the store and is handed to the learner as a sample weight, so a
doubtful observation contributes proportionally less to the fit rather than
either poisoning it or vanishing from it.

Four independent signals, combined multiplicatively because they fail for
unrelated reasons and any one of them being severe should dominate:

``bounds``
    Distance into a per-commodity plausible envelope. Catches unit errors
    (per-kilogram quoted where per-quintal is expected), decimal slips and
    stuck fields.

``internal``
    ``min <= modal <= max`` and the width of that spread. Free, and available
    from the live feed which publishes all three; the historical archive
    mostly does not carry min/max, so this signal abstains there rather than
    penalising rows for a column that was never collected.

``temporal``
    Deviation from the series' own recent median, scaled by that series'
    own robust volatility.

``cross_sectional``
    Deviation from what *other mandis trading the same commodity on the same
    day* printed. This is the signal the previous gate had no access to: a
    threefold jump in Kolar tomato is ordinary when Chickballapur and Malur
    jumped with it, and is almost certainly an error when it happens alone.
    It abstains below a quorum of peers, because a "cross-section" of two
    markets carries no information about what is normal.

Only the genuinely impossible is still hard-rejected. Everything else is
priced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.validation import DEFAULT_BOUNDS, PRICE_BOUNDS
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

QUALITY_SCORE_COLUMN = "quality_score"
QUALITY_FLAGS_COLUMN = "quality_flags"

FLAG_OUT_OF_BOUNDS = "out_of_plausible_range"
FLAG_NON_POSITIVE = "non_positive_price"
FLAG_MISSING_FIELD = "missing_required_field"
FLAG_SPREAD_INVERTED = "modal_outside_min_max"
FLAG_SPREAD_WIDE = "implausible_spread"
FLAG_TEMPORAL_OUTLIER = "temporal_outlier"
FLAG_CROSS_SECTIONAL_OUTLIER = "cross_sectional_outlier"
FLAG_UNIT_SUSPECT = "suspected_unit_change"

_MAD_TO_SIGMA = 1.4826
_EPSILON = 1e-9


@dataclass(frozen=True)
class QualityConfig:
    """Tunables for graded scoring."""

    soft_bounds_log_margin: float = 1.0
    """Ramp width at each end of the envelope, in natural-log units (1.0 is
    roughly a factor of e ~ 2.7). `PRICE_BOUNDS` is deliberately set far wider
    than any real price so it only ever fires on values that cannot be a price
    of this commodity at all — which means the envelope spans a large
    multiplicative range (25x-450x, floor to ceiling). A margin defined as a
    *fraction of that span* would then cover thousands of rupees and penalise
    completely ordinary mid-range prices for no reason; a margin defined in
    log space penalises only a price actually approaching the true edge,
    regardless of how wide the envelope itself is."""

    max_spread_ratio: float = 1.5
    """(max - min) / modal above which the quoted spread stops being credible."""

    max_spread_ratio_hard_multiple: float = 6.0
    """The internal-consistency signal reaches 0 at `max_spread_ratio` times
    this multiple. Wide relative to the soft threshold on purpose: a wide
    quoted spread is unusual but not impossible (thin trading, a volatile
    day), so it should cost confidence rather than zero the record outright —
    zeroing is reserved for signals that agree the row is genuinely bad."""

    temporal_sigma_soft: float = 4.0
    """Robust z against the series' own history where penalty begins."""

    temporal_sigma_hard: float = 10.0
    """Robust z at which the temporal signal scores 0."""

    temporal_reference_window: int = 21
    temporal_min_history: int = 8

    cross_sigma_soft: float = 4.0
    cross_sigma_hard: float = 12.0
    cross_min_peers: int = 4
    """Below this many peer markets on the same commodity-day there is no
    usable cross-section and the signal abstains."""

    unit_change_log_ratio: float = 2.0
    """|log(price / reference)| near log(10)=2.3 or log(100)=4.6 with an
    otherwise normal cross-section is the signature of a unit switch rather
    than a price move."""

    hard_reject_score: float = 0.05
    """Below this the record is treated as unusable rather than merely weak."""

    min_weight: float = 0.05
    """Floor on the emitted score so an accepted row always carries some
    weight; a zero-weight row is a deleted row by another name."""


DEFAULT_QUALITY_CONFIG = QualityConfig()


@dataclass
class QualityReport:
    """What a scoring pass saw."""

    received: int = 0
    accepted: int = 0
    rejected: int = 0
    reasons: Dict[str, int] = field(default_factory=dict)
    flag_counts: Dict[str, int] = field(default_factory=dict)
    score_mean: float = 1.0
    score_p05: float = 1.0
    score_min: float = 1.0
    signal_abstentions: Dict[str, int] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        return (self.rejected / self.received) if self.received else 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "received": self.received,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "rejection_rate": round(self.rejection_rate, 4),
            "reasons": dict(self.reasons),
            "flag_counts": dict(self.flag_counts),
            "score_mean": round(self.score_mean, 4),
            "score_p05": round(self.score_p05, 4),
            "score_min": round(self.score_min, 4),
            "signal_abstentions": dict(self.signal_abstentions),
            "samples": self.samples[:10],
        }


def price_bounds(commodity: str) -> Tuple[float, float]:
    return PRICE_BOUNDS.get(str(commodity).lower(), DEFAULT_BOUNDS)


def _ramp(value: float, soft: float, hard: float) -> float:
    """1.0 below `soft`, falling linearly to 0.0 at `hard`."""
    if not np.isfinite(value):
        return 1.0
    if value <= soft:
        return 1.0
    if value >= hard:
        return 0.0
    return float(1.0 - (value - soft) / (hard - soft))


def _bounds_signal(price: float, commodity: str, config: QualityConfig) -> float:
    """
    1.0 comfortably inside the plausible envelope, ramping down only as the
    price approaches the true floor or ceiling.

    Distance is measured in log space rather than as a fraction of the raw
    span: `PRICE_BOUNDS` is intentionally very wide (it exists to catch unit
    errors and decimal slips, not to second-guess ordinary volatility), so a
    linear margin would treat a large chunk of perfectly normal mid-range
    prices as suspect purely because the envelope itself is wide.
    """
    floor, ceiling = price_bounds(commodity)
    if price < floor or price > ceiling:
        return 0.0
    if floor <= 0 or ceiling <= 0:
        return 1.0

    margin = max(config.soft_bounds_log_margin, _EPSILON)
    log_price, log_floor, log_ceiling = np.log(price), np.log(floor), np.log(ceiling)

    lower_room = (log_price - log_floor) / margin
    upper_room = (log_ceiling - log_price) / margin
    return float(np.clip(min(lower_room, upper_room, 1.0), 0.0, 1.0))


def _internal_signal(
    price: float,
    low: Optional[float],
    high: Optional[float],
    config: QualityConfig,
) -> Tuple[float, List[str]]:
    """Consistency of the (min, modal, max) triple. Abstains when min/max absent."""
    flags: List[str] = []
    if low is None or high is None or not np.isfinite(low) or not np.isfinite(high):
        return 1.0, flags
    if low <= 0 or high <= 0:
        return 1.0, flags

    score = 1.0
    if not (low <= price <= high):
        flags.append(FLAG_SPREAD_INVERTED)
        score *= 0.3

    spread_ratio = (high - low) / (price + _EPSILON)
    if spread_ratio > config.max_spread_ratio:
        flags.append(FLAG_SPREAD_WIDE)
        hard = config.max_spread_ratio * config.max_spread_ratio_hard_multiple
        score *= _ramp(spread_ratio, config.max_spread_ratio, hard)

    return float(np.clip(score, 0.0, 1.0)), flags


def _series_reference(history: pd.DataFrame, config: QualityConfig) -> Dict[Tuple[str, str], Tuple[float, float]]:
    """
    Per-series (median price, robust sigma of log returns).

    Sigma is the MAD of day-over-day log returns scaled to a normal-equivalent
    standard deviation. Using each series' own dispersion is what makes one
    threshold meaningful across markets with genuinely different volatility.
    """
    reference: Dict[Tuple[str, str], Tuple[float, float]] = {}
    if history is None or history.empty:
        return reference

    frame = history[["date", "commodity", "mandi_id", "modal_price"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame = frame.dropna(subset=["date", "modal_price"])
    frame = frame[frame["modal_price"] > 0].sort_values("date")

    for key, group in frame.groupby(["commodity", "mandi_id"], sort=False):
        if len(group) < config.temporal_min_history:
            continue
        recent = group["modal_price"].tail(config.temporal_reference_window)
        median = float(recent.median())
        if median <= 0:
            continue

        log_returns = np.diff(np.log(group["modal_price"].to_numpy()))
        log_returns = log_returns[np.isfinite(log_returns)]
        if log_returns.size < config.temporal_min_history:
            sigma = float("nan")
        else:
            mad = float(np.median(np.abs(log_returns - np.median(log_returns))))
            sigma = mad * _MAD_TO_SIGMA if mad > 0 else float("nan")

        reference[key] = (median, sigma)

    return reference


def _cross_sectional_reference(
    frame: pd.DataFrame,
    config: QualityConfig,
) -> Dict[Tuple[str, pd.Timestamp], Tuple[float, float, int]]:
    """
    Per (commodity, date) peer median and robust dispersion of log prices.

    This is the signal the previous validator could not compute: what the rest
    of the country was printing for the same commodity on the same day.
    """
    reference: Dict[Tuple[str, pd.Timestamp], Tuple[float, float, int]] = {}
    if frame is None or frame.empty:
        return reference

    work = frame[["date", "commodity", "modal_price"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    work["modal_price"] = pd.to_numeric(work["modal_price"], errors="coerce")
    work = work.dropna(subset=["date", "modal_price"])
    work = work[work["modal_price"] > 0]
    if work.empty:
        return reference

    work["log_price"] = np.log(work["modal_price"])

    for key, group in work.groupby(["commodity", "date"], sort=False):
        n_peers = len(group)
        if n_peers < config.cross_min_peers:
            continue
        logs = group["log_price"].to_numpy()
        median_log = float(np.median(logs))
        mad = float(np.median(np.abs(logs - median_log)))
        sigma = mad * _MAD_TO_SIGMA if mad > 0 else float("nan")
        reference[key] = (median_log, sigma, n_peers)

    return reference


def score_observations(
    records: pd.DataFrame,
    history: Optional[pd.DataFrame] = None,
    config: QualityConfig = DEFAULT_QUALITY_CONFIG,
) -> Tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    """
    Score incoming observations and split them by usability.

    Args:
        records: candidate observations conforming to the store schema.
        history: existing observations, used to build the temporal reference.
            When absent the temporal signal abstains rather than guessing.
        config: scoring tunables.

    Returns:
        ``(accepted, rejected, report)``. `accepted` carries `quality_score`
        and `quality_flags`; `rejected` carries the same plus the reason, and
        is written to quarantine by the caller rather than discarded.
    """
    report = QualityReport()

    if records is None or records.empty:
        empty = pd.DataFrame(columns=getattr(records, "columns", None))
        return empty, empty.copy(), report

    frame = records.copy()
    report.received = len(frame)

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ("modal_price", "min_price", "max_price"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            frame[column] = np.nan

    series_reference = _series_reference(history, config) if history is not None else {}

    # The cross-section is built from the incoming batch plus same-day history.
    # A nightly pull returns many markets for one day, which is exactly the
    # cross-section this signal needs.
    cross_source = frame
    if history is not None and not history.empty:
        incoming_dates = set(frame["date"].dropna().dt.normalize().unique())
        if incoming_dates:
            hist = history.copy()
            hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
            same_day = hist[hist["date"].dt.normalize().isin(incoming_dates)]
            if not same_day.empty:
                cross_source = pd.concat([frame, same_day], ignore_index=True)
    cross_reference = _cross_sectional_reference(cross_source, config)

    scores: List[float] = []
    flag_lists: List[str] = []
    reasons: List[Optional[str]] = []
    abstentions = {"internal": 0, "temporal": 0, "cross_sectional": 0}

    for row in frame.itertuples(index=False):
        commodity = getattr(row, "commodity", None)
        mandi_id = getattr(row, "mandi_id", None)
        date = getattr(row, "date", None)
        price = getattr(row, "modal_price", None)

        if not commodity or not mandi_id or pd.isna(date):
            scores.append(0.0)
            flag_lists.append(FLAG_MISSING_FIELD)
            reasons.append(FLAG_MISSING_FIELD)
            continue

        if price is None or pd.isna(price) or price <= 0:
            scores.append(0.0)
            flag_lists.append(FLAG_NON_POSITIVE)
            reasons.append(FLAG_NON_POSITIVE)
            continue

        price = float(price)
        flags: List[str] = []

        bounds_score = _bounds_signal(price, commodity, config)
        if bounds_score <= 0.0:
            scores.append(0.0)
            flag_lists.append(FLAG_OUT_OF_BOUNDS)
            reasons.append(FLAG_OUT_OF_BOUNDS)
            continue

        low = getattr(row, "min_price", np.nan)
        high = getattr(row, "max_price", np.nan)
        low = None if low is None or pd.isna(low) else float(low)
        high = None if high is None or pd.isna(high) else float(high)
        internal_score, internal_flags = _internal_signal(price, low, high, config)
        flags.extend(internal_flags)
        if low is None or high is None:
            abstentions["internal"] += 1

        temporal_score = 1.0
        reference = series_reference.get((commodity, mandi_id))
        if reference is None or not np.isfinite(reference[1]) or reference[1] <= 0:
            abstentions["temporal"] += 1
        else:
            median, sigma = reference
            deviation = abs(float(np.log(price / median)))
            z = deviation / (sigma + _EPSILON)
            temporal_score = _ramp(z, config.temporal_sigma_soft, config.temporal_sigma_hard)
            if temporal_score < 1.0:
                flags.append(FLAG_TEMPORAL_OUTLIER)

        cross_score = 1.0
        cross_key = (commodity, pd.Timestamp(date).normalize())
        cross = cross_reference.get(cross_key)
        if cross is None or not np.isfinite(cross[1]) or cross[1] <= 0:
            abstentions["cross_sectional"] += 1
        else:
            median_log, sigma_log, _ = cross
            deviation = abs(float(np.log(price)) - median_log)
            z = deviation / (sigma_log + _EPSILON)
            cross_score = _ramp(z, config.cross_sigma_soft, config.cross_sigma_hard)
            if cross_score < 1.0:
                flags.append(FLAG_CROSS_SECTIONAL_OUTLIER)
            # A move that is large against the peer cross-section *and* close
            # to a power of ten is a unit switch, not a price. Worth its own
            # flag because the remedy is rescaling, not rejection.
            if deviation > config.unit_change_log_ratio:
                for step in (np.log(10.0), np.log(100.0)):
                    if abs(deviation - step) < 0.5:
                        flags.append(FLAG_UNIT_SUSPECT)
                        break

        score = bounds_score * internal_score * temporal_score * cross_score
        score = float(np.clip(score, 0.0, 1.0))

        if score < config.hard_reject_score:
            scores.append(score)
            flag_lists.append("|".join(flags) if flags else FLAG_TEMPORAL_OUTLIER)
            reasons.append(flags[0] if flags else FLAG_TEMPORAL_OUTLIER)
            continue

        scores.append(max(score, config.min_weight))
        flag_lists.append("|".join(flags))
        reasons.append(None)

    frame[QUALITY_SCORE_COLUMN] = scores
    frame[QUALITY_FLAGS_COLUMN] = flag_lists
    frame["reject_reason"] = reasons

    rejected = frame[frame["reject_reason"].notna()].copy()
    accepted = frame[frame["reject_reason"].isna()].drop(columns=["reject_reason"]).copy()

    report.accepted = int(len(accepted))
    report.rejected = int(len(rejected))
    report.signal_abstentions = abstentions

    for reason, count in rejected["reject_reason"].value_counts().items():
        report.reasons[str(reason)] = int(count)

    flag_counter: Dict[str, int] = {}
    for entry in accepted[QUALITY_FLAGS_COLUMN]:
        if not entry:
            continue
        for flag in str(entry).split("|"):
            if flag:
                flag_counter[flag] = flag_counter.get(flag, 0) + 1
    report.flag_counts = flag_counter

    if not accepted.empty:
        accepted_scores = accepted[QUALITY_SCORE_COLUMN].to_numpy(dtype="float64")
        report.score_mean = float(np.mean(accepted_scores))
        report.score_p05 = float(np.quantile(accepted_scores, 0.05))
        report.score_min = float(np.min(accepted_scores))

    for row in rejected.head(10).itertuples(index=False):
        report.samples.append(
            {
                "date": str(getattr(row, "date", ""))[:10],
                "commodity": getattr(row, "commodity", None),
                "mandi_id": getattr(row, "mandi_id", None),
                "modal_price": getattr(row, "modal_price", None),
                "quality_score": round(float(getattr(row, "quality_score", 0.0)), 4),
                "reason": getattr(row, "reject_reason", None),
            }
        )

    if report.rejected:
        logger.warning(
            "Quality scoring quarantined %d/%d rows: %s",
            report.rejected, report.received, report.reasons,
        )
    else:
        logger.info(
            "Quality scoring accepted all %d rows (mean score %.3f, p05 %.3f)",
            report.received, report.score_mean, report.score_p05,
        )

    return accepted, rejected, report
