'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { GitBranch, Info } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice } from './shared';
import { traderApi, type TransmissionEdge } from '@/services/traderApi';

/**
 * Cross-commodity transmission — does a glut or squeeze in one crop move
 * another crop's price, in the same district?
 *
 * This is the honest sibling of a "correlation heatmap": every one of the 40
 * tested edges is shown, not just the ones that passed, because a trader
 * deciding whether to act on an apparent pattern needs to see the filter the
 * pattern had to clear (FDR correction, a circular-shift placebo, a
 * pre-shock check, and agreement across districts) — not a single p-value.
 * On the current panel zero edges clear all four; that is reported as the
 * finding, not hidden by only drawing what passed.
 */

const CROPS = ['tomato', 'onion', 'potato', 'ginger', 'garlic'];
const TIER_COLOUR: Record<TransmissionEdge['tier'], string> = {
  ROBUST: 'var(--bullish, #16a34a)',
  SUGGESTIVE: 'var(--accent)',
  // Tested and found not significant still has to read as "a measurement
  // happened here", not as an empty cell — otherwise the one honest finding
  // of this panel (nothing survives the full filter) looks like missing
  // data instead of a result. A visible neutral fill, not a near-black one.
  NOT_SIGNIFICANT: 'var(--neutral-signal, #8a8a94)',
  INSUFFICIENT_EVIDENCE: 'transparent',
};

export default function TransmissionMatrix() {
  const [shock, setShock] = useState<'glut' | 'squeeze'>('glut');
  const [hover, setHover] = useState<TransmissionEdge | null>(null);
  const { data, isFetching } = useQuery({
    queryKey: ['trader-transmission-matrix'],
    queryFn: () => traderApi.transmissionMatrix(),
    staleTime: 10 * 60 * 1000,
  });

  const grid = useMemo(() => {
    const map = new Map<string, TransmissionEdge>();
    (data?.edges ?? []).filter((e) => e.shock === shock).forEach((e) => map.set(`${e.source}>${e.target}`, e));
    return map;
  }, [data, shock]);

  return (
    <ToolCard
      title="Cross-Commodity Transmission"
      subtitle={data?.status === 'OK' ? `${data.n_robust} of ${data.n_tested} edges robust · ${data.data_from}–${data.data_to}` : undefined}
      icon={<GitBranch className="h-4.5 w-4.5" />}
      accent="var(--intelligence)"
    >
      {isFetching && <LoadingRow label="Loading transmission matrix…" />}
      {data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {data?.status === 'OK' && (
        <div>
          <div className="mb-3 flex items-center gap-1.5">
            {(['glut', 'squeeze'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setShock(s)}
                className="rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide transition-colors"
                style={{ background: shock === s ? 'var(--accent-soft)' : 'transparent', color: shock === s ? 'var(--accent-strong)' : 'var(--neutral-signal)' }}
              >
                {s === 'glut' ? 'After a glut' : 'After a squeeze'}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-separate" style={{ borderSpacing: 3 }}>
              <thead>
                <tr>
                  <th className="w-16 text-left text-[9px] font-bold uppercase text-neutral-signal">Source \ Target</th>
                  {CROPS.map((c) => (
                    <th key={c} className="px-1 pb-1 text-center text-[9px] font-bold uppercase text-neutral-signal">{c.slice(0, 4)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CROPS.map((source) => (
                  <tr key={source}>
                    <td className="pr-2 text-[10px] font-bold capitalize text-foreground">{source}</td>
                    {CROPS.map((target) => {
                      if (source === target) return <td key={target} className="h-9 rounded-md bg-transparent" />;
                      const edge = grid.get(`${source}>${target}`);
                      if (!edge) return <td key={target} className="h-9 rounded-md border border-dashed border-border/40" />;
                      const mag = edge.effect != null ? Math.min(1, Math.abs(edge.effect) / 0.12) : 0;
                      return (
                        <td key={target} className="p-0">
                          <motion.button
                            onMouseEnter={() => setHover(edge)}
                            onMouseLeave={() => setHover((h) => (h === edge ? null : h))}
                            whileHover={{ scale: 1.08 }}
                            className="h-9 w-full rounded-md border border-border/40"
                            style={{
                              background: edge.tier === 'NOT_SIGNIFICANT'
                                ? `color-mix(in srgb, ${TIER_COLOUR[edge.tier]} ${22 + mag * 28}%, transparent)`
                                : `color-mix(in srgb, ${TIER_COLOUR[edge.tier]} ${38 + mag * 50}%, transparent)`,
                              borderColor: edge.tier === 'ROBUST' ? TIER_COLOUR.ROBUST : undefined,
                            }}
                            aria-label={`${source} to ${target}, ${edge.tier}`}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-neutral-signal">
            <Legend colour={TIER_COLOUR.ROBUST} label="Robust (survives FDR + placebo + stability)" />
            <Legend colour={TIER_COLOUR.SUGGESTIVE} label="Suggestive (passes FDR, fails placebo or stability)" />
            <Legend colour={TIER_COLOUR.NOT_SIGNIFICANT} label="Not significant" />
          </div>

          <div className="mt-3 min-h-[4.5rem] rounded-xl border border-border bg-surface-1 p-3">
            {hover ? (
              <div className="text-xs">
                <p className="font-bold text-foreground">
                  {hover.source} → {hover.target} <span className="font-normal text-neutral-signal">({shock})</span>
                </p>
                {hover.status === 'OK' ? (
                  <p className="mt-1 leading-relaxed text-neutral-signal">
                    effect {((hover.effect ?? 0) * 100).toFixed(1)}% [{((hover.ci?.[0] ?? 0) * 100).toFixed(1)}, {((hover.ci?.[1] ?? 0) * 100).toFixed(1)}] ·
                    {' '}placebo p={hover.placebo_p?.toFixed(2)} · pre-trend t={hover.pre_trend_t?.toFixed(1)} ·
                    {' '}stable in {hover.stability?.agree}/{hover.stability?.districts} districts ·
                    {' '}n={hover.n_episodes} episodes
                    {hover.tier !== 'ROBUST' && hover.min_detectable_effect != null && (
                      <> — minimum effect this test could detect: {(hover.min_detectable_effect * 100).toFixed(1)}%</>
                    )}
                  </p>
                ) : (
                  <p className="mt-1 text-neutral-signal">Too few episodes to test.</p>
                )}
              </div>
            ) : (
              <p className="flex items-center gap-1.5 text-xs text-neutral-signal"><Info className="h-3.5 w-3.5" /> Hover a cell for its full evidence.</p>
            )}
          </div>
        </div>
      )}
    </ToolCard>
  );
}

function Legend({ colour, label }: { colour: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2.5 w-2.5 rounded-sm border border-border/40" style={{ background: colour === TIER_COLOUR.NOT_SIGNIFICANT ? 'color-mix(in srgb, ' + colour + ' 40%, transparent)' : colour }} />
      {label}
    </span>
  );
}
