'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { rupees } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';
import ProduceIcon, { produceScript, resolveProduce } from './ProduceIcon';

/**
 * A slow, looping band of every crop in the district with its recorded price
 * and 7-day move: the same overview query the crop rail uses. Renders nothing
 * until that data exists, and holds still under reduced motion or on hover.
 */
export default function PriceTicker() {
  const { district } = useFarm();
  const { lang } = useLanguage();
  const { data } = useQuery({
    queryKey: ['farm-overview', district],
    queryFn: () => farmerApi.overview(district),
  });
  if (!data?.crops?.length) return null;

  const row = (copy: number) =>
    data.crops.map((c) => {
      const up = (c.d7 ?? 0) >= 0;
      return (
        <li key={`${copy}-${c.crop}`} aria-hidden={copy > 0 || undefined} className="flex shrink-0 items-center gap-3 px-6">
          <ProduceIcon name={c.crop} px={30} plated={false} />
          <span className="text-sm font-extrabold uppercase tracking-wider text-[var(--forest)]">{produceScript(resolveProduce(c.crop), lang).text}</span>
          <span className="farm-display text-xl font-extrabold tabular-nums text-[var(--forest)]">{rupees(c.price)}</span>
          {c.d7 != null && (
            <span className="rounded-full bg-[var(--forest)] px-2 py-0.5 text-xs font-bold tabular-nums text-[var(--lime)]">
              {up ? '▲' : '▼'} {Math.abs(c.d7).toFixed(1)}%
            </span>
          )}
          <span className="text-[var(--forest)]/40" aria-hidden="true">✦</span>
        </li>
      );
    });

  return (
    <div className="farm-ticker relative overflow-hidden bg-[var(--lime)] py-3" role="region" aria-label="Crop prices">
      <ul className="farm-ticker-track flex w-max items-center">
        {[0, 1, 2, 3].map((copy) => row(copy))}
      </ul>
    </div>
  );
}
