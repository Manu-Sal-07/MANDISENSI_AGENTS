'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Sprout } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { MandiPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type CropPlanningResult } from '@/services/farmerApi';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export default function CropPlanningTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { mandiId } = useToolSelection();
  const [month, setMonth] = useState(new Date().getMonth() + 1);

  const { data, isFetching } = useQuery<CropPlanningResult>({
    queryKey: ['crop-planning', mandiId, month],
    queryFn: () => farmerApi.cropPlanning(mandiId, month),
    enabled: open,
  });

  const crops = data?.crops ?? [];
  const maxDeviation = Math.max(1, ...crops.map((c) => Math.abs(c.avg_deviation_from_own_yearly_mean_pct)));

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="What to Plant Next"
      subtitle="Seasonal patterns across crops at your mandi"
      accentColour="var(--leaf)"
      icon={<Sprout className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <MandiPicker />
        <label className="block">
          <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
            Harvest month
          </span>
          <select
            value={month}
            onChange={(event) => setMonth(Number(event.target.value))}
            className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold text-[var(--farm-ink)]"
          >
            {MONTHS.map((name, index) => (
              <option key={name} value={index + 1}>
                {name}
              </option>
            ))}
          </select>
        </label>

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Reading years of seasonal pattern…
          </div>
        )}

        {!isFetching && data?.status !== 'OK' && (
          <UnavailableNotice reason={'reason' in (data || {}) ? (data as any).reason : undefined} />
        )}

        {!isFetching && data?.status === 'OK' && (
          <div className="space-y-3">
            <p className="rounded-xl bg-[var(--farm-line)]/40 px-3.5 py-2.5 text-xs leading-relaxed text-[var(--farm-ink-faint)]">
              {data.disclaimer}
            </p>
            {crops.map((crop, index) => {
              const positive = crop.avg_deviation_from_own_yearly_mean_pct >= 0;
              const width = (Math.abs(crop.avg_deviation_from_own_yearly_mean_pct) / maxDeviation) * 100;
              return (
                <motion.div
                  key={crop.commodity}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.06 }}
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-bold capitalize text-[var(--farm-ink)]">
                      {crop.commodity.replace('_', ' ')}
                    </span>
                    <span
                      className="font-mono font-bold"
                      style={{ color: positive ? 'var(--leaf-deep)' : 'var(--tomato)' }}
                    >
                      {positive ? '+' : ''}
                      {crop.avg_deviation_from_own_yearly_mean_pct}%
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[var(--farm-line)]">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: positive ? 'var(--leaf)' : 'var(--tomato)' }}
                      initial={{ width: 0 }}
                      animate={{ width: `${width}%` }}
                      transition={{ delay: index * 0.06 + 0.1, duration: 0.5 }}
                    />
                  </div>
                  <p className="mt-0.5 text-[11px] text-[var(--farm-ink-faint)]">
                    {crop.years_observed} year(s) of data · consistent {crop.consistency}% of the time
                  </p>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
