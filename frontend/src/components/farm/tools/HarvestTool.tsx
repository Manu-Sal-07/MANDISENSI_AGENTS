'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Sparkles, Wallet } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker, QuantityPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type HarvestPlan } from '@/services/farmerApi';
import { formatDate, formatRupees } from '@/lib/format';

export default function HarvestTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId, quantityQuintals } = useToolSelection();

  const { data, isFetching } = useQuery<HarvestPlan>({
    queryKey: ['harvest-plan', commodity, mandiId, quantityQuintals],
    queryFn: () => farmerApi.harvestPlan(commodity, mandiId, quantityQuintals),
    enabled: open,
  });

  const priced = (data?.days ?? []).filter((d) => d.expected_total !== null);
  const maxTotal = Math.max(1, ...priced.map((d) => d.range_high ?? d.expected_total ?? 0));

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="My Harvest in Rupees"
      subtitle="What your crop is worth on each day ahead"
      accentColour="var(--leaf-deep)"
      icon={<Wallet className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <div className="grid grid-cols-2 gap-3">
          <MandiPicker />
          <QuantityPicker />
        </div>

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Working out your harvest&rsquo;s value…
          </div>
        )}

        {!isFetching && data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {!isFetching && data?.status === 'OK' && (
          <div className="space-y-2.5">
            {priced.map((day, index) => {
              const isBest = day.target_date === data.best_day;
              const barWidth = ((day.range_high ?? day.expected_total ?? 0) / maxTotal) * 100;
              const lowWidth = ((day.range_low ?? day.expected_total ?? 0) / maxTotal) * 100;
              return (
                <motion.div
                  key={`${day.horizon_days}-${day.target_date}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.06, duration: 0.35 }}
                  className="rounded-2xl border p-3.5"
                  style={{
                    borderColor: isBest ? 'var(--leaf)' : 'var(--farm-line)',
                    background: isBest ? 'var(--leaf-wash)' : 'var(--farm-paper)',
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-sm font-bold text-[var(--farm-ink)]">
                      {day.horizon_days === 0 ? 'Today' : formatDate(day.target_date)}
                      {isBest && <Sparkles className="h-3.5 w-3.5" style={{ color: 'var(--leaf)' }} />}
                    </span>
                    <span className="font-mono text-sm font-black text-[var(--farm-ink)]">
                      {formatRupees(day.expected_total)}
                    </span>
                  </div>

                  <div className="relative mt-2 h-2.5 w-full overflow-hidden rounded-full bg-[var(--farm-line)]">
                    <motion.div
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{ background: isBest ? 'var(--leaf)' : 'var(--farm-line-strong)' }}
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ delay: index * 0.06 + 0.1, duration: 0.5, ease: 'easeOut' }}
                    />
                    <motion.div
                      className="absolute inset-y-0 left-0 rounded-full opacity-40"
                      style={{ background: isBest ? 'var(--leaf-deep)' : 'var(--farm-ink-faint)' }}
                      initial={{ width: 0 }}
                      animate={{ width: `${lowWidth}%` }}
                      transition={{ delay: index * 0.06 + 0.15, duration: 0.5, ease: 'easeOut' }}
                    />
                  </div>

                  {day.range_low !== null && day.range_high !== null && (
                    <p className="mt-1 font-mono text-xs text-[var(--farm-ink-faint)]">
                      {formatRupees(day.range_low)} – {formatRupees(day.range_high)}
                    </p>
                  )}
                </motion.div>
              );
            })}

            {(data.days ?? []).filter((d) => d.expected_total === null).map((day) => (
              <div
                key={`refused-${day.horizon_days}`}
                className="rounded-xl border border-dashed border-[var(--farm-line)] px-3.5 py-2.5 text-xs text-[var(--farm-ink-faint)]"
              >
                {day.label}: {day.reason || 'not enough data yet'}
              </div>
            ))}
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
