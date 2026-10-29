'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatRupees } from './shared';
import { marketChoiceApi } from '@/services/marketChoiceApi';

const SELECT =
  'rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold capitalize text-foreground outline-none focus:ring-2 focus:ring-accent/30';
const SERIES = [
  { key: 'recommended', label: 'Model recommendation', colour: '#22c55e' },
  { key: 'highest', label: 'Highest price yesterday', colour: '#f59e0b' },
  { key: 'nearest', label: 'Nearest mandi, today', colour: '#94a3b8' },
  { key: 'oracle', label: 'Hindsight oracle', colour: '#a78bfa' },
] as const;

function LineChart({ months, series }: { months: string[]; series: Record<string, number[]> }) {
  const w = 640, h = 220, pad = { l: 46, r: 12, t: 12, b: 26 };
  const all = SERIES.flatMap((s) => series[s.key] ?? []);
  if (!all.length) return null;
  const lo = Math.min(...all) * 0.95, hi = Math.max(...all) * 1.03;
  const x = (i: number) => pad.l + (i / Math.max(months.length - 1, 1)) * (w - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * (h - pad.t - pad.b);
  const ticks = [lo, (lo + hi) / 2, hi];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Mean net revenue by month for the model, two rules and the oracle">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity={0.1} />
          <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" fontSize="9" fill="currentColor" opacity={0.6}>{Math.round(t)}</text>
        </g>
      ))}
      {months.map((m, i) => (i % 2 === 0 ? <text key={m} x={x(i)} y={h - 8} textAnchor="middle" fontSize="9" fill="currentColor" opacity={0.6}>{m.slice(2)}</text> : null))}
      {SERIES.map((s) => (
        <polyline key={s.key} fill="none" stroke={s.colour} strokeWidth={s.key === 'recommended' ? 2.4 : 1.5}
          strokeDasharray={s.key === 'oracle' ? '4 3' : undefined}
          points={(series[s.key] ?? []).map((v, i) => `${x(i)},${y(v)}`).join(' ')} />
      ))}
    </svg>
  );
}

/**
 * Floor Monitor: the track record of the market-choice advice, per crop.
 *
 * Everything here is out of sample: each block is predicted by a model fitted
 * strictly before it, and the floor is scored only on days after a burn-in.
 * It states plainly when a crop's advice did not beat simply going to the
 * mandi with yesterday's highest price ("limited evidence").
 */
export default function FloorMonitor() {
  const [crop, setCrop] = useState('tomato');
  const { data: info } = useQuery({ queryKey: ['mc-crops'], queryFn: () => marketChoiceApi.crops(), staleTime: 10 * 60 * 1000 });
  const { data, isFetching } = useQuery({ queryKey: ['mc-calibration', crop], queryFn: () => marketChoiceApi.calibration(crop) });
  const bt = data?.backtest;
  const rev = bt?.mean_net_revenue;
  const maxRev = rev ? Math.max(...Object.values(rev)) : 1;

  return (
    <ToolCard
      title="Floor Monitor"
      subtitle="Out-of-sample track record of the market-choice advice and of its revenue floor"
      icon={<ShieldCheck className="h-4.5 w-4.5" />}
      accent="#22c55e"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className={SELECT}>
          {(info?.crops ?? [{ crop: 'tomato' }]).map((c) => (
            <option key={c.crop} value={c.crop}>{c.crop}</option>
          ))}
        </select>
        {data?.status === 'OK' && bt && (
          <span
            className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
            style={{
              background: bt.level === 'strong' ? 'color-mix(in oklch, var(--bullish) 18%, transparent)' : 'rgba(245,158,11,.15)',
              color: bt.level === 'strong' ? 'var(--bullish)' : '#f59e0b',
            }}
          >
            {bt.level === 'strong' ? 'Evidence: strong' : 'Evidence: limited'}
          </span>
        )}
      </div>

      {isFetching && <LoadingRow label="Loading the backtest…" />}
      {!isFetching && data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {!isFetching && data?.status === 'OK' && bt && rev && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { k: 'Scored days', v: String(bt.scored_days), s: `${bt.window?.[0]} → ${bt.window?.[1]}` },
              { k: 'Gain vs highest yesterday', v: `${bt.gain_vs_highest_yesterday!.mean >= 0 ? '+' : ''}${formatRupees(bt.gain_vs_highest_yesterday!.mean)}/q`,
                s: `95% CI ${formatRupees(bt.gain_vs_highest_yesterday!.ci_lo)} … ${formatRupees(bt.gain_vs_highest_yesterday!.ci_hi)}` },
              { k: 'Gain vs nearest mandi', v: `+${formatRupees(bt.gain_vs_nearest!.mean)}/q`, s: `95% CI ${formatRupees(bt.gain_vs_nearest!.ci_lo)} … ${formatRupees(bt.gain_vs_nearest!.ci_hi)}` },
              { k: 'Silent-mandi trips', v: `${Math.round((bt.silent_trip_rate ?? 0) * 100)}%`, s: 'of recommended trips' },
            ].map((t) => (
              <div key={t.k} className="rounded-xl border border-border bg-surface-2 px-3 py-2.5">
                <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">{t.k}</p>
                <p className="mt-0.5 font-mono text-base font-black tabular-nums text-foreground">{t.v}</p>
                <p className="text-[10px] text-neutral-signal">{t.s}</p>
              </div>
            ))}
          </div>

          <div>
            <p className="mb-2 text-xs font-bold text-foreground">Mean net revenue by policy (₹ per quintal)</p>
            <div className="space-y-1.5">
              {[
                ['recommended', 'Model recommendation'], ['safest', 'Best-floor alternative'], ['highest_yesterday', 'Highest price yesterday'],
                ['nearest', 'Nearest mandi, today'], ['farm_gate', 'Farm gate'], ['oracle', 'Hindsight oracle'],
              ].map(([k, label]) => (
                <div key={k} className="flex items-center gap-2 text-xs">
                  <span className="w-40 shrink-0 text-neutral-signal">{label}</span>
                  <div className="h-3 flex-1 rounded-full bg-surface-2">
                    <div className="h-3 rounded-full" style={{ width: `${(100 * rev[k]) / maxRev}%`, background: k === 'recommended' ? '#22c55e' : k === 'oracle' ? '#a78bfa' : '#64748b' }} />
                  </div>
                  <span className="w-16 text-right font-mono font-bold tabular-nums text-foreground">{formatRupees(rev[k])}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-1 text-xs font-bold text-foreground">Monthly net revenue (₹/q)</p>
            <div className="text-foreground">
              <LineChart months={bt.monthly.months} series={bt.monthly as unknown as Record<string, number[]>} />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-neutral-signal">
              {SERIES.map((s) => (
                <span key={s.key} className="flex items-center gap-1.5"><span className="h-0.5 w-4" style={{ background: s.colour }} />{s.label}</span>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-bold text-foreground">Floor calibration: how often the stated floor was broken</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="py-1 text-left font-bold">Target</th>
                  <th className="py-1 text-right font-bold">Adaptive (served)</th>
                  <th className="py-1 text-right font-bold">Static, out of sample</th>
                  <th className="py-1 text-right font-bold">Multiplier q</th>
                </tr>
              </thead>
              <tbody>
                {(data.alphas ?? []).map((a) => {
                  const k = a.toFixed(2);
                  const adaptive = bt.floor_violation_adaptive?.[k];
                  const ok = adaptive !== undefined && Math.abs(adaptive - a) <= 0.03;
                  return (
                    <tr key={k} className="border-t border-border">
                      <td className="py-1.5 font-bold text-foreground">{Math.round(a * 100)}%</td>
                      <td className="py-1.5 text-right font-mono tabular-nums" style={{ color: ok ? 'var(--bullish)' : '#f59e0b' }}>{adaptive !== undefined ? `${(adaptive * 100).toFixed(1)}%` : '—'}</td>
                      <td className="py-1.5 text-right font-mono tabular-nums text-neutral-signal">{bt.floor_violation_static_out_of_sample?.[k] !== undefined ? `${(bt.floor_violation_static_out_of_sample[k] * 100).toFixed(1)}%` : '—'}</td>
                      <td className="py-1.5 text-right font-mono tabular-nums text-neutral-signal">{data.multiplier_q?.[k] ?? '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="mt-2 text-[11px] leading-relaxed text-neutral-signal">
              The adaptive floor is the one served: its level is nudged online, with delayed feedback, so the broken-floor rate tracks the target without
              assuming any distribution. Green means within 3 points of the target. Choosing by the floor instead of by expected revenue (&quot;best-floor alternative&quot;) earned {formatRupees(rev.safest)}/q against {formatRupees(rev.recommended)}/q for the recommendation in this window; the app recommends the best expected option and attaches the floor to it, because the study found choosing by the floor usually gives up expected revenue. Check the bars above for this crop.
            </p>
          </div>
        </div>
      )}
    </ToolCard>
  );
}
