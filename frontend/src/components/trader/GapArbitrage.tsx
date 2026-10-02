'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowRight, Waves } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, CommodityPicker, formatPct } from './shared';
import { traderApi } from '@/services/traderApi';

/**
 * Cross-district gap arbitrage — the same-crop sibling of the spread
 * scanner above, but built on district-level price gaps shown (by Test B's
 * error-correction fit, mandisense_ai/farmer/transmission.py) to actually
 * mean-revert, with a measured half-life, rather than on the scanner's own
 * per-mandi AR(1) fit. Projects today's gap forward to the trip's arrival
 * date using that pair's own measured speed of closure, so the number
 * traded on is "what the gap will likely be on arrival", not "what it is
 * today".
 */
export default function GapArbitrage() {
  const [commodity, setCommodity] = useState('ginger');
  const [tripDays, setTripDays] = useState(3);
  const { data, isFetching } = useQuery({
    queryKey: ['trader-gap-arbitrage', commodity, tripDays],
    queryFn: () => traderApi.transmissionGaps(commodity, 20, tripDays),
  });

  return (
    <ToolCard
      title="Cross-District Gap Arbitrage"
      subtitle="Same crop, two districts — gaps shown to actually close"
      icon={<Waves className="h-4.5 w-4.5" />}
      accent="var(--bullish, #16a34a)"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <CommodityPicker value={commodity} onChange={setCommodity} />
        <label className="flex items-center gap-1.5 text-xs text-neutral-signal">
          Trip
          <input
            type="number"
            min={1}
            max={14}
            value={tripDays}
            onChange={(e) => setTripDays(Math.max(1, Math.min(14, Number(e.target.value) || 1)))}
            className="w-12 rounded-md border border-border bg-surface-1 px-1.5 py-1 text-center text-xs text-foreground"
          />
          days
        </label>
      </div>

      {isFetching && <LoadingRow label="Scanning district gaps…" />}
      {data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {data?.status === 'OK' && (
        <div className="space-y-2">
          {(data.pairs ?? []).slice(0, 6).map((row, i) => (
            <motion.div
              key={`${row.cheaper_district}-${row.dearer_district}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-xl border p-3"
              style={{ borderColor: row.worth_hauling ? 'color-mix(in srgb, var(--bullish, #16a34a) 40%, var(--border))' : 'var(--border)' }}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="flex items-center gap-1.5 text-xs font-bold capitalize text-foreground">
                  {row.cheaper_district.replace(/_/g, ' ')}
                  <ArrowRight className="h-3 w-3 text-neutral-signal" />
                  {row.dearer_district.replace(/_/g, ' ')}
                </p>
                <p className="font-mono text-sm font-bold" style={{ color: row.worth_hauling ? 'var(--bullish, #16a34a)' : 'var(--neutral-signal)' }}>
                  {formatPct(row.net_gross_margin_pct)} net
                </p>
              </div>
              <div className="mt-2 grid grid-cols-4 gap-2 text-[10px] text-neutral-signal">
                <Stat label="Today" value={formatPct(row.current_gap_pct)} />
                <Stat label="On arrival" value={formatPct(row.projected_gap_pct_on_arrival)} />
                <Stat label="Half-life" value={`${row.half_life_weeks}w`} />
                <Stat label="Transport" value={row.distance_km != null ? `${row.distance_km}km` : '—'} />
              </div>
            </motion.div>
          ))}
          {!data.pairs?.length && (
            <p className="py-6 text-center text-xs text-neutral-signal">No closing gap found for {commodity}.</p>
          )}
          <p className="pt-1 text-[10px] leading-relaxed text-neutral-signal/80">{data.assumption}</p>
        </div>
      )}
    </ToolCard>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex flex-col">
      <span className="uppercase tracking-wide">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </span>
  );
}
