'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Route, Truck } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, CommodityPicker, formatRupees, formatPct } from './shared';
import { traderApi } from '@/services/traderApi';

/**
 * Mandi-to-mandi spread scanner.
 *
 * The one number that matters is `expected_net_on_arrival_per_quintal`, not
 * the sticker gap — see `trader/arbitrage.py`. A spread whose own history
 * says it typically closes before the truck gets there is shown, but pushed
 * below every spread the model expects to still be there on arrival, with
 * the reasoning (AR(1) reversion vs. a random walk) visible per row rather
 * than asserted.
 */
export default function SpreadScanner() {
  const [commodity, setCommodity] = useState('tomato');
  const [quantity, setQuantity] = useState(20);

  const { data, isFetching } = useQuery({
    queryKey: ['trader-spreads', commodity, quantity],
    queryFn: () => traderApi.spreads(commodity, quantity, 8),
  });

  return (
    <ToolCard
      title="Mandi Spread Scanner"
      subtitle="Net margin expected to still be there on arrival, not today's gap"
      icon={<Route className="h-4.5 w-4.5" />}
      accent="#22d3ee"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <CommodityPicker value={commodity} onChange={setCommodity} />
        <input
          type="number"
          min={1}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
          className="w-24 rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold tabular-nums text-foreground outline-none focus:ring-2 focus:ring-accent/30"
        />
        <span className="text-xs text-neutral-signal">quintals</span>
      </div>

      {isFetching && <LoadingRow label="Scanning inter-mandi spreads…" />}
      {!isFetching && data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {!isFetching && data?.status === 'OK' && (
        <div className="space-y-2">
          <p className="text-[11px] text-neutral-signal">
            {data.mandis_compared} mandis compared as of {data.as_of} · {data.survivors} survive the trip,{' '}
            {data.vanishing} don&rsquo;t
          </p>
          {(data.opportunities ?? []).map((op, i) => (
            <motion.div
              key={`${op.buy_mandi}-${op.sell_mandi}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-xl border p-3"
              style={{
                borderColor: op.survives_trip ? 'var(--bullish)' : 'var(--border)',
                background: op.survives_trip ? 'color-mix(in oklch, var(--bullish) 8%, transparent)' : 'var(--surface-2)',
                opacity: op.survives_trip ? 1 : 0.6,
              }}
            >
              <div className="flex items-center justify-between text-xs font-bold text-foreground">
                <span className="flex items-center gap-1.5">
                  {op.buy_mandi_name} <ArrowRight className="h-3 w-3 text-neutral-signal" /> {op.sell_mandi_name}
                </span>
                <span className="font-mono tabular-nums" style={{ color: op.survives_trip ? 'var(--bullish)' : 'var(--neutral-signal)' }}>
                  {formatRupees(op.expected_net_on_arrival_per_quintal)}/q
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-neutral-signal">
                <span className="flex items-center gap-1">
                  <Truck className="h-3 w-3" /> {op.vehicle} · {op.distance_km}km · {op.trip_days}d
                </span>
                <span>today {formatRupees(op.today_net_per_quintal)}/q</span>
                <span>
                  {op.model === 'ar1_mean_reversion'
                    ? `reverts, half-life ${op.half_life_days}d`
                    : op.model === 'random_walk'
                    ? 'no measurable reversion'
                    : 'no shared history'}
                </span>
                {op.closure?.rate != null && <span>closed {formatPct(op.closure.rate * 100, 0)} of similar past gaps</span>}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </ToolCard>
  );
}
