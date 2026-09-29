'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { FlaskConical } from 'lucide-react';
import { ToolCard, LoadingRow, formatPct } from './shared';
import { traderApi } from '@/services/traderApi';

/**
 * Evidence-based scenarios — replaces the Intelligence Lab's
 * counterfactuals, which were hand-written formulas (e.g. "Arrival
 * Increase" was `basePct + diff(0.25) - forecast*0.05`) consulting no data
 * about how this series actually responds to anything. Every scenario here
 * is a condition evaluated on the series' own history
 * (`trader/scenarios.py`), de-clustered into independent episodes and gated
 * on a minimum sample size before any outcome is shown.
 */
export default function ScenariosPanel({ commodity, mandiId }: { commodity: string; mandiId: string }) {
  const { data, isFetching } = useQuery({
    queryKey: ['trader-scenarios', commodity, mandiId],
    queryFn: () => traderApi.scenarios(commodity, mandiId),
  });

  const usable = (data?.scenarios ?? []).filter((s) => s.status === 'OK');

  return (
    <ToolCard
      title="Evidence-Based Scenarios"
      subtitle="What happened, historically, after conditions like today's"
      icon={<FlaskConical className="h-4.5 w-4.5" />}
      accent="#fb923c"
    >
      {isFetching && <LoadingRow label="Testing scenarios against history…" />}

      {!isFetching && usable.length === 0 && (
        <p className="py-4 text-xs text-neutral-signal">
          Not enough independent past episodes yet for any scenario on this series.
        </p>
      )}

      {!isFetching && usable.length > 0 && (
        <div className="space-y-2">
          {usable.map((s, i) => (
            <motion.div
              key={s.scenario}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-xl bg-surface-2 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                  {s.label}
                  {s.condition_active_now && (
                    <span className="rounded-full bg-accent/20 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wide text-accent">
                      active now
                    </span>
                  )}
                </span>
                <span className="font-mono text-xs font-black" style={{ color: (s.outcome?.median_pct ?? 0) >= 0 ? 'var(--bullish)' : 'var(--bearish)' }}>
                  {formatPct(s.outcome?.median_pct)}
                </span>
              </div>
              <p className="mt-1 text-[10px] text-neutral-signal">{s.definition}</p>
              <p className="mt-1 text-[10px] text-neutral-signal">
                {s.episodes} episodes · edge vs baseline {formatPct(s.edge_vs_baseline_pct)}
              </p>
            </motion.div>
          ))}
          <p className="pt-1 text-[10px] italic text-neutral-signal">
            {usable[0]?.disclaimer}
          </p>
        </div>
      )}
    </ToolCard>
  );
}
