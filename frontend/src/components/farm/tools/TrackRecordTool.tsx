'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Award, Loader2, Target } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker } from './ContextPicker';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type TrackRecordResult } from '@/services/farmerApi';

function Stat({ label, value, delay }: { label: string; value: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, type: 'spring', stiffness: 260, damping: 22 }}
      className="rounded-2xl border border-[var(--farm-line)] px-4 py-3.5 text-center"
    >
      <p className="farm-display text-2xl text-[var(--farm-ink)]">{value}</p>
      <p className="mt-0.5 text-xs font-semibold text-[var(--farm-ink-faint)]">{label}</p>
    </motion.div>
  );
}

export default function TrackRecordTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId } = useToolSelection();

  const { data, isFetching } = useQuery<TrackRecordResult>({
    queryKey: ['track-record', commodity, mandiId],
    queryFn: () => farmerApi.trackRecord(commodity, mandiId),
    enabled: open,
  });

  const pct = (value?: number | null) => (value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`);

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Did We Get It Right?"
      subtitle="Our own scorecard, checked against real outcomes"
      accentColour="#7a4fd1"
      icon={<Award className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <MandiPicker />

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking past forecasts against what happened…
          </div>
        )}

        {!isFetching && (data?.status === 'NO_RECORDS' || data?.status === 'INSUFFICIENT_EVIDENCE') && (
          <div className="flex items-start gap-3 rounded-2xl border border-[var(--farm-line)] px-4 py-4">
            <Target className="mt-0.5 h-4 w-4 shrink-0 text-[var(--farm-ink-faint)]" />
            <div>
              <p className="text-sm font-bold text-[var(--farm-ink)]">Not enough resolved calls yet</p>
              <p className="mt-1 text-sm leading-relaxed text-[var(--farm-ink-faint)]">
                {data.note ||
                  `${data.scored ?? 0} scored outcome(s) so far — a track record needs a real sample before it means anything.`}
              </p>
            </div>
          </div>
        )}

        {!isFetching && data?.status === 'OK' && (
          <div className="grid grid-cols-2 gap-2.5">
            <Stat label="Direction called correctly" value={pct(data.directional_accuracy)} delay={0} />
            <Stat label="SELL/HOLD calls were right" value={pct(data.decision_precision)} delay={0.06} />
            <Stat label="Price landed in 90% band" value={pct(data.coverage_90)} delay={0.12} />
            <Stat label={`Based on ${data.scored} calls`} value={String(data.decision_calls ?? '—')} delay={0.18} />
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
