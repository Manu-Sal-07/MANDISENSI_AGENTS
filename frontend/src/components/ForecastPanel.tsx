'use client';

/**
 * Phase 2 forecast panel.
 *
 * Renders the published forecast curve for one (commodity, mandi) series.
 *
 * Three things this component deliberately does *not* do, because the system
 * behind it is built on them:
 *
 * 1. It never invents a number. A series can be refused
 *    (INSUFFICIENT_HISTORY, DORMANT, REBUILDING_HISTORY,
 *    NO_PROMOTED_MODEL) and the refusal is rendered as the answer, with its
 *    reason, rather than as an empty state or a zero.
 *
 * 2. It never shows a point estimate without its interval. Measured skill
 *    over a naive "price unchanged" forecast is a few percent, so the point
 *    alone would overstate what the model knows. The 90% band is empirical —
 *    it comes from how wrong the model actually was on held-out folds — and
 *    it is the decision-relevant output.
 *
 * 3. It never implies the number is live. Forecasts come from a scheduled
 *    offline job, so the as-of date and staleness are shown on the panel
 *    itself rather than left for the reader to assume.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Clock, Minus } from 'lucide-react';
import { mandiApi, type ForecastCurve, type ForecastPoint } from '@/services/api';

interface ForecastPanelProps {
  commodity: string;
  mandiId: string;
}

const REFUSAL_COPY: Record<string, string> = {
  INSUFFICIENT_HISTORY: 'Not enough history',
  DORMANT: 'Series dormant',
  REBUILDING_HISTORY: 'Rebuilding history after a gap',
  DISCONTINUOUS_HISTORY: 'History has a gap',
  NO_PROMOTED_MODEL: 'No model cleared the baseline',
};

const formatRupees = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '--';
  return `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;
};

const formatMandi = (mandiId: string) =>
  mandiId.replace(/_apmc$/, '').replace(/_/g, ' ').toUpperCase();

const DECISION_STYLE: Record<string, string> = {
  SELL: 'border-rose-900/50 bg-rose-950/30 text-rose-300',
  HOLD: 'border-emerald-900/50 bg-emerald-950/30 text-emerald-300',
  WAIT: 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
};

/**
 * Where this row's band came from.
 *
 * Not decoration. A row-conditional band is this series' own volatility on
 * this date; a pooled band is a single fold-fixed offset applied to every
 * row alike. They carry different weight and the reader cannot tell them
 * apart by looking, so the panel says which one it drew.
 */
const INTERVAL_SOURCE_COPY: Record<string, string> = {
  row_conditional_quantile: "band from this row's own volatility",
  pooled_residual: 'band pooled across all rows',
};

function HorizonRow({ point, basePrice }: { point: ForecastPoint; basePrice: number | null }) {
  const refused = point.status !== 'OK';

  if (refused) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-amber-900/40 bg-amber-950/20 px-4 py-3">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
        <div className="min-w-0">
          <div className="text-[11px] font-black uppercase tracking-wider text-amber-400">
            {point.horizon_days ? `${point.horizon_days}-day · ` : ''}
            {REFUSAL_COPY[point.status] ?? point.status}
          </div>
          {point.reason && (
            <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">{point.reason}</p>
          )}
        </div>
      </div>
    );
  }

  const up = point.direction === 'up';
  const flat = point.expected_change_pct === 0 || point.direction === null;
  const DirIcon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  const dirColor = flat ? 'text-zinc-400' : up ? 'text-emerald-400' : 'text-rose-400';

  const band = point.interval;
  // The band is drawn relative to the span it occupies, so the point's
  // position inside its own interval is visible rather than implied.
  let markerPct: number | null = null;
  if (band?.p05 != null && band?.p95 != null && point.forecast_price != null && band.p95 > band.p05) {
    markerPct = ((point.forecast_price - band.p05) / (band.p95 - band.p05)) * 100;
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
          {point.horizon_days}-day
          {point.target_date && (
            <span className="ml-2 font-mono font-normal normal-case tracking-normal text-zinc-600">
              {point.target_date}
            </span>
          )}
        </span>
        <span className={`inline-flex items-center gap-1 text-sm font-black tabular-nums ${dirColor}`}>
          <DirIcon className="h-3.5 w-3.5" />
          {point.expected_change_pct != null
            ? `${point.expected_change_pct > 0 ? '+' : ''}${point.expected_change_pct.toFixed(2)}%`
            : '--'}
        </span>
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-mono text-xl font-black tabular-nums text-zinc-100">
          {formatRupees(point.forecast_price)}
        </span>
        {basePrice != null && (
          <span className="text-[11px] text-zinc-600">from {formatRupees(basePrice)}</span>
        )}
      </div>

      {band?.p05 != null && band?.p95 != null && (
        <div className="mt-3">
          <div className="relative h-1.5 w-full rounded-full bg-zinc-800">
            {/* interquartile range, drawn inside the 90% band */}
            {band.p25 != null && band.p75 != null && band.p95 > band.p05 && (
              <div
                className="absolute inset-y-0 rounded-full bg-zinc-600"
                style={{
                  left: `${((band.p25 - band.p05) / (band.p95 - band.p05)) * 100}%`,
                  width: `${((band.p75 - band.p25) / (band.p95 - band.p05)) * 100}%`,
                }}
              />
            )}
            {markerPct != null && (
              <div
                className="absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-400"
                style={{ left: `${Math.min(100, Math.max(0, markerPct))}%` }}
              />
            )}
          </div>
          <div className="mt-1.5 flex items-center justify-between font-mono text-[10px] tabular-nums text-zinc-600">
            <span>{formatRupees(band.p05)}</span>
            <span className="font-sans text-[9px] font-black uppercase tracking-widest text-zinc-700">
              90% interval
            </span>
            <span>{formatRupees(band.p95)}</span>
          </div>
        </div>
      )}

      {/* The calibrated recommendation and what backs it. Every one of these
          fields was already published by the backend and typed here, and
          none of them was rendered anywhere — the decision policy, its
          measured probability and the interval's provenance all stopped at
          the type definition and never reached a reader. */}
      {(point.decision || point.model_skill != null) && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-zinc-800 pt-2.5 text-[10px] text-zinc-600">
          {point.decision && (
            <span
              className={`rounded border px-1.5 py-0.5 text-[9px] font-black uppercase tracking-widest ${
                DECISION_STYLE[point.decision] ?? DECISION_STYLE.WAIT
              }`}
            >
              {point.decision}
            </span>
          )}
          {point.decision_probability_of_decline != null && (
            <span>
              P(fall){' '}
              <span className="font-mono tabular-nums text-zinc-400">
                {(point.decision_probability_of_decline * 100).toFixed(0)}%
              </span>
            </span>
          )}
          {point.model_skill != null && (
            <span>
              Skill vs naive{' '}
              <span className="font-mono tabular-nums text-zinc-500">
                {(point.model_skill * 100).toFixed(1)}%
              </span>
            </span>
          )}
          {point.interval_source && (
            <span className="text-zinc-700">
              {INTERVAL_SOURCE_COPY[point.interval_source] ?? point.interval_source}
            </span>
          )}
          {point.prediction_source === 'xgboost_linear_blend' && (
            <span className="text-zinc-700">blended with a linear model</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function ForecastPanel({ commodity, mandiId }: ForecastPanelProps) {
  const [curve, setCurve] = useState<ForecastCurve | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    mandiApi
      .getForecast(commodity, mandiId)
      .then((data) => {
        if (!cancelled) setCurve(data);
      })
      .catch((err) => {
        // A missing series is a legitimate answer from a scheduled system,
        // not a client fault, so it is reported as absence rather than as a
        // broken panel.
        if (!cancelled) setError(err instanceof Error ? err.message : 'Forecast unavailable');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [commodity, mandiId]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 p-6">
        <div className="h-3 w-40 animate-pulse rounded bg-zinc-800" />
        <div className="mt-4 space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-zinc-900/60" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !curve) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 p-6">
        <h3 className="mb-3 text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
          Scheduled Forecast
        </h3>
        <div className="flex items-start gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-500" />
          <p className="text-[11px] leading-relaxed text-zinc-400">
            No published forecast for {commodity.toUpperCase()} · {formatMandi(mandiId)}. The
            nightly job publishes a series only once it holds enough history to forecast it.
          </p>
        </div>
      </div>
    );
  }

  const stale = curve.freshness && curve.freshness !== 'FRESH';

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 p-6 shadow-md">
      <h3 className="mb-1 flex items-center justify-between text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
        <span>Scheduled Forecast</span>
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] normal-case tracking-normal text-zinc-600">
          <Clock className="h-3 w-3" />
          as of {curve.as_of_date ?? '--'}
        </span>
      </h3>

      <p className="mb-4 text-[10px] leading-relaxed text-zinc-600">
        Published by the nightly batch job — not computed on this request.
        {curve.history_rows != null && ` ${curve.history_rows} observations held.`}
        {curve.last_observed_price != null &&
          ` Last close ${formatRupees(curve.last_observed_price)}.`}
      </p>

      {stale && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-900/40 bg-amber-950/20 px-3 py-2">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
          <span className="text-[10px] text-amber-400">
            Store freshness: {curve.freshness}
            {curve.data_lag_days != null && ` · data lag ${curve.data_lag_days}d`}
          </span>
        </div>
      )}

      <div className="space-y-3">
        {curve.points.map((point, i) => (
          <HorizonRow
            key={`${point.horizon_days ?? 'refused'}-${i}`}
            point={point}
            basePrice={curve.last_observed_price}
          />
        ))}
      </div>

      <p className="mt-4 border-t border-zinc-800 pt-3 text-[10px] leading-relaxed text-zinc-600">
        The interval, not the point, is the decision-relevant output. Bands are empirical: they
        reflect how wrong this model actually was on held-out historical folds, not a normality
        assumption. Measured skill over a naive &ldquo;price unchanged&rdquo; forecast is a few
        percent.
      </p>
    </div>
  );
}
