'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Droplets, Loader2, Waves } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type SupplySignalResult } from '@/services/farmerApi';
import { formatDate } from '@/lib/format';

const SIGNAL_COPY: Record<string, { label: string; colour: string; wash: string }> = {
  FLOOD: { label: 'More arriving than usual', colour: '#b8801a', wash: 'var(--turmeric-wash)' },
  DROUGHT: { label: 'Less arriving than usual', colour: 'var(--tomato)', wash: 'var(--tomato-wash)' },
  NORMAL: { label: 'Arrivals are typical', colour: 'var(--leaf-deep)', wash: 'var(--leaf-wash)' },
};

export default function SupplySignalTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId } = useToolSelection();

  const { data, isFetching } = useQuery<SupplySignalResult>({
    queryKey: ['supply-signal', commodity, mandiId],
    queryFn: () => farmerApi.supplySignal(commodity, mandiId),
    enabled: open,
  });

  const signal = data?.signal ? SIGNAL_COPY[data.signal] : null;

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Supply Signal"
      subtitle="Is too much (or too little) arriving?"
      accentColour="#2f8fd9"
      icon={<Waves className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <MandiPicker />

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Reading arrival volumes…
          </div>
        )}

        {!isFetching && (data?.status === 'UNAVAILABLE' || data?.status === 'INSUFFICIENT_HISTORY') && (
          <UnavailableNotice reason={data.reason} />
        )}

        {!isFetching && data?.status === 'OK' && signal && (
          <>
            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', stiffness: 280, damping: 22 }}
              className="rounded-2xl p-5 text-center"
              style={{ background: signal.wash }}
            >
              <Droplets className="mx-auto h-8 w-8" style={{ color: signal.colour }} />
              <p className="farm-display mt-2 text-2xl" style={{ color: signal.colour }}>
                {signal.label}
              </p>
              <p className="mt-1 font-mono text-sm font-bold text-[var(--farm-ink-soft)]">
                {data.deviation_pct! > 0 ? '+' : ''}
                {data.deviation_pct}% vs the usual level
              </p>
            </motion.div>

            {!data.is_live_reading && (
              <p className="rounded-xl bg-[var(--farm-line)]/40 px-3.5 py-2.5 text-xs text-[var(--farm-ink-faint)]">
                Based on the last recorded arrival print ({formatDate(data.as_of_date)}, {data.data_age_days} day(s)
                old) — the live feed does not currently carry arrival volumes for this series.
              </p>
            )}

            {data.historical_note && (
              <p className="rounded-xl border border-[var(--farm-line)] px-3.5 py-2.5 text-sm text-[var(--farm-ink-soft)]">
                {data.historical_note}
              </p>
            )}
          </>
        )}
      </div>
    </ToolSheet>
  );
}
