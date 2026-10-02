'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { History } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatPct } from './shared';
import { traderApi } from '@/services/traderApi';

/**
 * Historical analog finder — replaces the Market Explorer's "Analogous
 * Historical Periods" panel, which read `historical_analogs` from
 * cognition state: empty on every one of the 75 tracked series. Every
 * number here comes from real nearest-neighbour search over the series'
 * own history (`trader/analogs.py`), reported against the unconditional
 * baseline so the outcome spread means something.
 */
export default function AnalogsPanel({ commodity, mandiId }: { commodity: string; mandiId: string }) {
  const { data, isFetching } = useQuery({
    queryKey: ['trader-analogs', commodity, mandiId],
    queryFn: () => traderApi.analogs(commodity, mandiId),
  });

  return (
    <ToolCard
      title="Historical Analogs"
      subtitle="When has this market looked like this before?"
      icon={<History className="h-4.5 w-4.5" />}
      accent="#a78bfa"
    >
      {isFetching && <LoadingRow label="Searching for similar past patterns…" />}
      {!isFetching && (data?.status === 'INSUFFICIENT_HISTORY' || data?.status === 'INSUFFICIENT_EVIDENCE') && (
        <RefusalNotice reason={data.reason} />
      )}

      {!isFetching && data?.status === 'OK' && data.outcome && (
        <>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl bg-surface-2 p-4"
          >
            <div className="flex items-baseline justify-between">
              <span className="text-xs font-semibold text-neutral-signal">
                {data.analogs?.length} analogs · {data.horizon_days}-day forward outcome
              </span>
              <span className="font-mono text-sm font-black text-foreground">
                {formatPct(data.outcome.median_pct)} median
              </span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-3">
              <div
                className="h-full rounded-full"
                style={{ width: `${data.outcome.share_up * 100}%`, background: 'var(--bullish)' }}
              />
            </div>
            <p className="mt-1.5 text-[10px] text-neutral-signal">
              rose {Math.round(data.outcome.share_up * 100)}% of the time here, vs{' '}
              {Math.round((data.baseline?.share_up ?? 0) * 100)}% unconditionally (n={data.baseline?.n})
            </p>
          </motion.div>

          <div className="mt-3 space-y-1.5">
            {(data.analogs ?? []).slice(0, 6).map((a, i) => (
              <motion.div
                key={a.start}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-center justify-between rounded-lg bg-surface-2 px-2.5 py-1.5 text-[11px]"
              >
                <span className="text-neutral-signal">
                  {a.start} → {a.end}
                </span>
                <span
                  className="font-mono font-bold"
                  style={{ color: a.forward_return_pct >= 0 ? 'var(--bullish)' : 'var(--bearish)' }}
                >
                  {formatPct(a.forward_return_pct)}
                </span>
              </motion.div>
            ))}
          </div>
          <p className="mt-2 text-[10px] italic text-neutral-signal">{data.disclaimer}</p>
        </>
      )}
    </ToolCard>
  );
}
