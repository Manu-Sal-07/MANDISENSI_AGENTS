'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScanSearch } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice } from './shared';
import { marketChoiceApi } from '@/services/marketChoiceApi';

const pct = (v: number, d = 0) => `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(d)}%`;

/** A centred bar: green to the right of zero for skill above the random walk, red to the left for below. */
function SkillBar({ value, colour }: { value: number; colour: string }) {
  const width = Math.min(Math.abs(value) / 0.8, 1) * 50;
  return (
    <div className="relative h-3 w-full rounded-full bg-surface-2">
      <span className="absolute left-1/2 top-0 h-3 w-px bg-border" />
      <span className="absolute top-0 h-3 rounded-full" style={{ width: `${width}%`, [value >= 0 ? 'left' : 'right']: '50%', background: colour } as React.CSSProperties} />
    </div>
  );
}

/**
 * Forecast Audit: do decomposition-based forecasters (STL, VMD hybrids) really beat a random walk?
 *
 * They do, when the series is decomposed once before the data are split: a
 * component on day t then depends on prices after day t. When every forecast
 * origin sees only the data available at that time, the advantage disappears.
 * The table is read straight from the study; nothing here is computed in the
 * browser.
 */
export default function ForecastAudit() {
  const { data, isFetching } = useQuery({ queryKey: ['mc-evidence'], queryFn: () => marketChoiceApi.evidence(), staleTime: 60 * 60 * 1000 });
  const rows = data?.leakage ?? [];

  return (
    <ToolCard
      title="Forecast Audit"
      subtitle="Decomposition forecasters look strong only if the decomposition may see the future"
      icon={<ScanSearch className="h-4.5 w-4.5" />}
      accent="#a78bfa"
    >
      {isFetching && <LoadingRow label="Loading the audit…" />}
      {!isFetching && data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}
      {!isFetching && data?.status === 'OK' && (
        <div className="space-y-5">
          <p className="text-sm leading-relaxed text-neutral-signal">
            Skill is the improvement in absolute error over a <b className="text-foreground">random walk</b> (“tomorrow equals today”). Positive is better than the
            random walk. <span style={{ color: '#ef4444' }}>Published</span> decomposes the whole series once, then splits.{' '}
            <span style={{ color: '#22c55e' }}>Causal</span> uses, at every forecast date, only the data that existed that day.
          </p>

          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full min-w-[640px] text-xs">
              <thead>
                <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="px-3 py-2 text-left font-bold">Method</th>
                  <th className="px-2 py-2 text-center font-bold">Horizon</th>
                  <th className="w-[28%] px-2 py-2 text-left font-bold">Published vs causal skill</th>
                  <th className="px-2 py-2 text-right font-bold">Published</th>
                  <th className="px-2 py-2 text-right font-bold">Causal</th>
                  <th className="px-2 py-2 text-right font-bold">Raw series</th>
                  <th className="px-2 py-2 text-right font-bold">Leak gap</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={`${r.decomposer}-${r.forecaster}-${r.h}`} className="border-t border-border">
                    <td className="px-3 py-2 font-bold text-foreground">{r.decomposer} + {r.forecaster}</td>
                    <td className="px-2 py-2 text-center text-neutral-signal">{r.h}d</td>
                    <td className="px-2 py-2">
                      <div className="space-y-1">
                        <SkillBar value={r.published_joint} colour="#ef4444" />
                        <SkillBar value={r.causal_joint} colour="#22c55e" />
                      </div>
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums" style={{ color: '#ef4444' }}>{pct(r.published_joint)}</td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums" style={{ color: '#22c55e' }}>{pct(r.causal_joint)}</td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-neutral-signal">{pct(r.raw)}</td>
                    <td className="px-2 py-2 text-right font-mono font-bold tabular-nums text-foreground">{(r.gap * 100).toFixed(0)} pp</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-surface-2 px-3 py-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Why it happens</p>
              <p className="mt-1 text-xs leading-relaxed text-foreground">
                Moving only the <i>future</i> changes today’s STL/VMD components by{' '}
                {(data.future_sensitivity ?? []).map((s) => `${(s.median * 100).toFixed(1)}% (${s.decomposer})`).join(' and ')} of the series’ spread. A causal method changes them by exactly zero.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 px-3 py-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Zero-shot foundation model</p>
              <p className="mt-1 text-xs leading-relaxed text-foreground">
                Chronos-Bolt, never trained on these prices: skill {pct(data.foundation_model?.['1'] ?? 0, 1)} at 1 day and {pct(data.foundation_model?.['7'] ?? 0, 1)} at 7 days.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 px-3 py-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">What this means</p>
              <p className="mt-1 text-xs leading-relaxed text-foreground">
                Daily price history alone is almost unpredictable here. The value is in the decision layer (which mandi, which day), not in a sharper price forecast.
              </p>
            </div>
          </div>
        </div>
      )}
    </ToolCard>
  );
}
