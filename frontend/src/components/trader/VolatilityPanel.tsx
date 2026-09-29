'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Waves } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice } from './shared';
import { traderApi } from '@/services/traderApi';

const REGIME_COLOR: Record<string, string> = {
  CALM: 'var(--bullish)',
  NORMAL: 'var(--neutral-signal)',
  TURBULENT: 'var(--bearish)',
};

/**
 * Realised volatility and regimes, computed from the series' own returns
 * (see `trader/volatility.py`) — replaces the Market Explorer's regime
 * timeline, which was permanently "Unknown" because the data it read never
 * carried a regime field on 65 of 75 series.
 */
export default function VolatilityPanel({ commodity, mandiId }: { commodity: string; mandiId: string }) {
  const { data, isFetching } = useQuery({
    queryKey: ['trader-volatility', commodity, mandiId],
    queryFn: () => traderApi.volatility(commodity, mandiId),
  });

  const regime = data?.current_regime;
  const accent = regime ? REGIME_COLOR[regime] : 'var(--accent)';

  return (
    <ToolCard
      title="Volatility & Regime"
      subtitle="Expanding percentile of this series' own volatility history"
      icon={<Waves className="h-4.5 w-4.5" />}
      accent={accent}
    >
      {isFetching && <LoadingRow label="Measuring realised volatility…" />}
      {!isFetching && data?.status === 'INSUFFICIENT_HISTORY' && <RefusalNotice reason={data.reason} />}

      {!isFetching && data?.status === 'OK' && (
        <>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-xl p-4 text-center"
            style={{ background: `${accent}14` }}
          >
            <p className="font-display text-xl font-black" style={{ color: accent }}>
              {regime}
            </p>
            <p className="mt-1 font-mono text-xs text-neutral-signal">
              20-print vol: {data.windows?.['20'].current_daily_pct}% daily (
              {data.windows?.['20'].percentile}th percentile of its own history)
            </p>
          </motion.div>

          <div className="mt-3 flex overflow-hidden rounded-full h-2">
            {(['CALM', 'NORMAL', 'TURBULENT'] as const).map((r) => (
              <div
                key={r}
                style={{
                  width: `${(data.regime_share?.[r] ?? 0) * 100}%`,
                  background: REGIME_COLOR[r],
                }}
              />
            ))}
          </div>
          <div className="mt-1.5 flex justify-between text-[10px] text-neutral-signal">
            {(['CALM', 'NORMAL', 'TURBULENT'] as const).map((r) => (
              <span key={r}>{r} {Math.round((data.regime_share?.[r] ?? 0) * 100)}%</span>
            ))}
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            {(['10', '20', '60'] as const).map((w) => (
              <div key={w} className="rounded-lg bg-surface-2 p-2">
                <p className="text-[9px] font-bold uppercase tracking-wider text-neutral-signal">{w}-print</p>
                <p className="font-mono text-xs font-bold text-foreground">{data.windows?.[w].current_daily_pct}%</p>
              </div>
            ))}
          </div>
        </>
      )}
    </ToolCard>
  );
}
