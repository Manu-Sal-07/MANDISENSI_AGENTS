'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, HandCoins, Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker, QuantityPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { useLanguage } from '@/context/LanguageContext';
import { farmerApi, type FairPriceResult } from '@/services/farmerApi';
import { formatRupees } from '@/lib/format';

const VERDICT_STYLE: Record<string, { colour: string; wash: string; Icon: typeof TrendingUp }> = {
  well_below: { colour: 'var(--call-sell)', wash: 'var(--call-sell-wash)', Icon: TrendingDown },
  below: { colour: '#b8801a', wash: 'var(--turmeric-wash)', Icon: TrendingDown },
  fair: { colour: 'var(--call-hold)', wash: 'var(--call-hold-wash)', Icon: CheckCircle2 },
  above: { colour: 'var(--call-hold)', wash: 'var(--call-hold-wash)', Icon: TrendingUp },
  well_above: { colour: 'var(--leaf-deep)', wash: 'var(--leaf-wash)', Icon: TrendingUp },
};

export default function FairPriceTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId, quantityQuintals } = useToolSelection();
  const { lang } = useLanguage();
  const [offer, setOffer] = useState('');
  const [checked, setChecked] = useState<number | null>(null);

  const { data, isFetching, refetch } = useQuery<FairPriceResult>({
    queryKey: ['fair-price', commodity, mandiId, checked, quantityQuintals],
    queryFn: () => farmerApi.fairPriceCheck(commodity, mandiId, checked as number, quantityQuintals),
    enabled: open && checked !== null,
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = Number(offer);
    if (value > 0) setChecked(value);
  };

  const verdict = data?.verdict ? VERDICT_STYLE[data.verdict] : null;

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Fair Price Check"
      subtitle="Is the trader's offer fair, right now?"
      accentColour="var(--tomato)"
      icon={<HandCoins className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <div className="grid grid-cols-2 gap-3">
          <MandiPicker />
          <QuantityPicker />
        </div>

        <form onSubmit={submit} className="flex items-end gap-2">
          <label className="block flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
              What price were you offered? (₹/quintal)
            </span>
            <input
              type="number"
              min={1}
              value={offer}
              onChange={(event) => setOffer(event.target.value)}
              placeholder="e.g. 1500"
              className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-lg font-bold tabular-nums text-[var(--farm-ink)] placeholder:font-normal placeholder:text-[var(--farm-ink-faint)]"
            />
          </label>
          <button
            type="submit"
            disabled={!offer || Number(offer) <= 0}
            className="farm-focus farm-tap shrink-0 rounded-xl px-5 text-sm font-bold text-white transition-opacity disabled:opacity-40"
            style={{ background: 'var(--tomato)' }}
          >
            Check
          </button>
        </form>

        {isFetching && (
          <div className="flex items-center gap-2 py-6 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking today&rsquo;s prices…
          </div>
        )}

        {!isFetching && data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {!isFetching && data?.status === 'OK' && verdict && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
            className="rounded-2xl p-5"
            style={{ background: verdict.wash }}
          >
            <div className="flex items-center gap-2.5">
              <verdict.Icon className="h-6 w-6" style={{ color: verdict.colour }} />
              <span className="text-lg font-black" style={{ color: verdict.colour }}>
                {formatRupees(data.offered_price)} / quintal
              </span>
            </div>
            <p className="mt-2 text-sm font-semibold leading-relaxed" style={{ color: verdict.colour }}>
              {data.message?.[lang === 'kn' ? 'kn' : 'en'] || data.message?.en}
            </p>

            {data.observed && (
              <div className="mt-4 border-t pt-3" style={{ borderColor: `${verdict.colour}33` }}>
                <p className="text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
                  Today&rsquo;s going rate ({data.observed.as_of_date})
                </p>
                <p className="mt-1 font-mono text-base font-bold text-[var(--farm-ink)]">
                  {formatRupees(data.observed.range_low)} – {formatRupees(data.observed.range_high)}
                </p>
              </div>
            )}

            {data.difference !== undefined && data.quantity_quintals && (
              <div className="mt-3 flex items-center justify-between rounded-xl bg-white/60 px-3.5 py-2.5">
                <span className="text-sm font-semibold text-[var(--farm-ink-soft)]">
                  For {data.quantity_quintals} quintal(s)
                </span>
                <span
                  className="font-mono text-base font-black"
                  style={{ color: data.difference! < 0 ? 'var(--tomato)' : 'var(--leaf-deep)' }}
                >
                  {data.difference! < 0 ? '−' : '+'}
                  {formatRupees(Math.abs(data.difference!))}
                </span>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </ToolSheet>
  );
}
