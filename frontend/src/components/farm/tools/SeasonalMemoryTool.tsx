'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Loader2 } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type SeasonalMemoryResult } from '@/services/farmerApi';
import { formatDate, formatRupees, formatSignedPct } from '@/lib/format';

function ComparisonRow({
  label,
  price,
  changePct,
  detail,
  delay,
}: {
  label: string;
  price: number;
  changePct: number | null;
  detail?: string;
  delay: number;
}) {
  const rising = (changePct ?? 0) > 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="rounded-2xl border border-[var(--farm-line)] px-4 py-3.5"
    >
      <p className="text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{label}</p>
      <div className="mt-1 flex items-baseline justify-between">
        <span className="font-mono text-xl font-black text-[var(--farm-ink)]">{formatRupees(price)}</span>
        {changePct !== null && (
          <span
            className="font-mono text-sm font-bold"
            style={{ color: rising ? 'var(--call-sell)' : 'var(--leaf-deep)' }}
          >
            {formatSignedPct(changePct)}
          </span>
        )}
      </div>
      {detail && <p className="mt-0.5 text-xs text-[var(--farm-ink-faint)]">{detail}</p>}
    </motion.div>
  );
}

export default function SeasonalMemoryTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId } = useToolSelection();

  const { data, isFetching } = useQuery<SeasonalMemoryResult>({
    queryKey: ['seasonal-memory', commodity, mandiId],
    queryFn: () => farmerApi.seasonalMemory(commodity, mandiId),
    enabled: open,
  });

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="This Time Last Year"
      subtitle="How today compares to seasons past"
      accentColour="var(--soil)"
      icon={<CalendarClock className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <MandiPicker />

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Looking back through the archive…
          </div>
        )}

        {!isFetching && data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {!isFetching && data?.status === 'OK' && (
          <div className="space-y-2.5">
            <ComparisonRow
              label={`Today (${formatDate(data.as_of_date)})`}
              price={data.current_price ?? 0}
              changePct={null}
              delay={0}
            />
            {data.last_year && (
              <ComparisonRow
                label={`Same time last year (${formatDate(data.last_year.date)})`}
                price={data.last_year.price}
                changePct={data.last_year.change_pct}
                detail="Positive change = today is higher than a year ago"
                delay={0.08}
              />
            )}
            {data.seasonal_norm && (
              <ComparisonRow
                label={`Usual price for this time of year (${data.seasonal_norm.reference_years} years of data)`}
                price={data.seasonal_norm.median_price}
                changePct={data.seasonal_norm.deviation_pct}
                detail="Positive change = today is above the seasonal norm"
                delay={0.16}
              />
            )}
            {!data.last_year && !data.seasonal_norm && (
              <p className="text-sm text-[var(--farm-ink-faint)]">
                Not enough years of history yet to compare against a season.
              </p>
            )}
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
