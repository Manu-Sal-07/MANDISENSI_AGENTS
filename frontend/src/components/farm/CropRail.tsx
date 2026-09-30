'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { rupees } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';
import ProduceIcon, { produceScript, resolveProduce } from './ProduceIcon';
import Spark from './charts/Spark';
import { toneOf } from './callTone';

/**
 * Every crop in the district, each as its last month of price and today's call.
 *
 * A swipeable strip rather than a grid: five crops or fifteen keep the same
 * rhythm, and the selected one lifts. The price and its signed change sit in
 * text beside the line, so nothing depends on reading a colour.
 */
export default function CropRail() {
  const { district, crop, setCrop } = useFarm();
  const { lang } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ['farm-overview', district],
    queryFn: () => farmerApi.overview(district),
  });

  if (isLoading || !data) {
    return (
      <div className="farm-scroll-x no-scrollbar">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="farm-row h-[7.5rem] w-[9rem] shrink-0 animate-pulse bg-white/70" />
        ))}
      </div>
    );
  }

  return (
    <ul className="farm-scroll-x no-scrollbar" role="tablist" aria-label="Crops">
      {data.crops.map((c) => {
        const selected = c.crop === crop;
        const produce = resolveProduce(c.crop);
        const tone = toneOf(c.call, lang);
        const up = (c.d7 ?? 0) >= 0;
        return (
          <li key={c.crop} className="shrink-0 snap-start">
            <motion.button
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setCrop(c.crop)}
              whileTap={{ scale: 0.97 }}
              className="farm-focus farm-row relative block w-[9.25rem] p-3.5 text-left sm:w-[10.5rem]"
              style={{
                borderColor: selected ? 'var(--leaf)' : undefined,
                boxShadow: selected ? '0 0 0 2px var(--leaf), 0 14px 28px -16px rgba(27,122,62,0.55)' : undefined,
                transform: selected ? 'translateY(-2px)' : undefined,
              }}
            >
              <div className="flex items-center justify-between">
                <ProduceIcon name={c.crop} size="sm" />
                <span className="flex items-center gap-1.5 text-[11px] font-bold" style={{ color: tone.colour }}>
                  <span className="block h-2 w-2 rounded-full" style={{ background: tone.colour }} />
                  {tone.key === 'range' ? '' : tone.label}
                </span>
              </div>
              <p className="mt-2.5 truncate text-sm font-bold text-[var(--farm-ink)]">{produceScript(produce, lang).text}</p>
              <p className="farm-display text-xl leading-tight text-[var(--farm-ink)]">{rupees(c.price)}</p>
              <div className="mt-1 flex items-end justify-between">
                <span className="text-xs font-semibold tabular-nums text-[var(--farm-ink-soft)]">
                  {c.d7 == null ? '' : `${up ? '▲' : '▼'} ${Math.abs(c.d7).toFixed(1)}%`}
                </span>
                <Spark values={c.spark} width={64} height={24} colour={selected ? 'var(--leaf)' : 'var(--farm-ink-soft)'} />
              </div>
            </motion.button>
          </li>
        );
      })}
    </ul>
  );
}
