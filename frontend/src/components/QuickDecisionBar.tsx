'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { mandiApi } from '@/services/api';
import { Zap, Loader2, MapPin } from 'lucide-react';
import CommodityGlyph from './CommodityGlyph';
import { resolveCall } from './farm/CallCard';

const DECISION_COLOR: Record<string, string> = {
  SELL: 'text-bearish',
  HOLD: 'text-bullish',
  WAIT: 'text-warning',
  // Absence is drawn as absence. Amber here read as a cautious call.
  UNKNOWN: 'text-neutral-signal',
};

const DECISION_LABEL: Record<string, string> = {
  SELL: 'SELL',
  HOLD: 'HOLD',
  WAIT: 'WAIT',
  UNKNOWN: 'NO READING',
};

export default function QuickDecisionBar() {
  const { data, isLoading } = useQuery({
    queryKey: ['quick-decisions'],
    queryFn: () => mandiApi.getQuickDecisions('bengaluru'),
    staleTime: 1000 * 60 * 2,
  });

  if (isLoading) {
    return (
      <div className="elite-card flex items-center gap-3 border-dashed p-6">
        <Loader2 className="h-4 w-4 animate-spin text-neutral-signal" />
        <span className="label-caps text-[10.5px]">Syncing with market agents…</span>
      </div>
    );
  }

  return (
    <div className="elite-card noise-overlay relative overflow-hidden p-6 sm:p-7">
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-40 blur-[70px]"
        style={{ background: 'var(--accent-glow)' }}
      />
      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-2xl"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--intelligence))', boxShadow: '0 8px 20px -8px var(--accent-glow)' }}
          >
            <Zap className="h-6 w-6 fill-current text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-bullish" />
              <span className="label-caps text-[10px]">{data?.location || 'Bengaluru Region'}</span>
            </div>
            <h3 className="font-display text-lg font-semibold tracking-tight text-foreground">
              Market Flash Advice
            </h3>
          </div>
        </div>

        <div className="no-scrollbar flex gap-3 overflow-x-auto pb-1 lg:pb-0">
          {data?.decisions.map((item: { commodity: string; decision: string; call_type?: string | null }, i: number) => {
            // `call_type` is authoritative: an UNAVAILABLE result still
            // carries the verb "WAIT", and rendering that verb is the bug.
            const call = resolveCall(item);
            return (
            <motion.div
              key={item.commodity}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35 }}
              className="group flex flex-none items-center gap-3.5 rounded-2xl border border-border bg-surface-1 px-4 py-3 transition-colors hover:border-border-strong"
            >
              <CommodityGlyph name={item.commodity} size="sm" />
              <div>
                <p className="label-caps text-[9px]">{item.commodity}</p>
                <p className={`text-base font-black tracking-tight ${DECISION_COLOR[call]}`}>
                  {DECISION_LABEL[call]}
                </p>
              </div>
            </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
