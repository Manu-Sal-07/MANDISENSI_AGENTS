'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Handshake } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatRupees } from './shared';
import { traderApi } from '@/services/traderApi';

/**
 * Fair forward price — the one place the farmer and trader halves of this
 * product meet (`trader/forward.py`): farmer's spoilage-adjusted floor vs
 * trader's risk-adjusted ceiling, split evenly when they overlap, refused
 * outright and explained when they don't.
 */
export default function ForwardPriceCalculator({ commodity, mandiId }: { commodity: string; mandiId: string }) {
  const [horizon, setHorizon] = useState(7);
  const [quantity, setQuantity] = useState(10);

  const { data, isFetching } = useQuery({
    queryKey: ['trader-forward', commodity, mandiId, horizon, quantity],
    queryFn: () => traderApi.forwardPrice(commodity, mandiId, horizon, quantity),
  });

  return (
    <ToolCard
      title="Fair Forward Price"
      subtitle="A contract price both sides can defend"
      icon={<Handshake className="h-4.5 w-4.5" />}
      accent="#34d399"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-[11px] text-neutral-signal">
          Days
          <input
            type="number"
            min={1}
            max={14}
            value={horizon}
            onChange={(e) => setHorizon(Math.min(14, Math.max(1, Number(e.target.value) || 1)))}
            className="w-14 rounded-lg border border-border bg-surface-2 px-2 py-1 text-xs font-semibold tabular-nums text-foreground"
          />
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-neutral-signal">
          Quintals
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
            className="w-16 rounded-lg border border-border bg-surface-2 px-2 py-1 text-xs font-semibold tabular-nums text-foreground"
          />
        </label>
      </div>

      {isFetching && <LoadingRow label="Pricing the contract…" />}
      {!isFetching && (data?.status === 'UNAVAILABLE' || data?.status === 'UNSUITABLE') && (
        <RefusalNotice reason={data.reason} />
      )}

      {!isFetching && data?.status === 'OK' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {data.deal_possible ? (
            <div className="rounded-xl bg-[color-mix(in_oklch,var(--bullish)_10%,transparent)] p-4 text-center">
              <p className="font-display text-2xl font-black" style={{ color: 'var(--bullish)' }}>
                {formatRupees(data.fair_price)}/quintal
              </p>
              <p className="mt-1 text-[11px] text-neutral-signal">
                Contract value {formatRupees(data.contract_value)} · both sides gain{' '}
                {formatRupees(data.farmer_surplus_per_quintal)}/quintal
              </p>
            </div>
          ) : (
            <RefusalNotice reason={data.reason} />
          )}

          <div className="mt-3 grid grid-cols-2 gap-2 text-center">
            <div className="rounded-lg bg-surface-2 p-2.5">
              <p className="text-[9px] font-bold uppercase tracking-wider text-neutral-signal">Farmer&rsquo;s floor</p>
              <p className="font-mono text-xs font-bold text-foreground">{formatRupees(data.farmer_floor)}</p>
            </div>
            <div className="rounded-lg bg-surface-2 p-2.5">
              <p className="text-[9px] font-bold uppercase tracking-wider text-neutral-signal">Trader&rsquo;s ceiling</p>
              <p className="font-mono text-xs font-bold text-foreground">{formatRupees(data.trader_ceiling)}</p>
            </div>
          </div>

          {data.caveat && <p className="mt-2 text-[10px] italic text-neutral-signal">{data.caveat}</p>}
        </motion.div>
      )}
    </ToolCard>
  );
}
