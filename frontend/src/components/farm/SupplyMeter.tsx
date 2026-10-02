'use client';

import React from 'react';
import { motion } from 'framer-motion';

import { useLanguage } from '@/context/LanguageContext';
import { say } from '@/lib/i18n/farmCopy';
import type { SupplySignalResult } from '@/services/farmerApi';

/**
 * How much of the crop reached the market compared with a normal day.
 *
 * Arrivals are the one lever a farmer can read before the price moves: a glut
 * usually pulls the price down within days, scarcity pushes it up. Drawn as a
 * three-zone meter with a marker, so "a lot more than usual" is a position,
 * not a percentage to interpret.
 */
export default function SupplyMeter({ supply }: { supply: SupplySignalResult }) {
  const { lang } = useLanguage();
  const dev = Math.max(-60, Math.min(60, supply.deviation_pct ?? 0));
  const at = ((dev + 60) / 120) * 100;

  return (
    <div>
      <div className="relative mt-3 h-3 overflow-visible rounded-full" style={{ background: 'linear-gradient(90deg, var(--turmeric-wash), var(--leaf-wash) 40%, var(--leaf-wash) 60%, var(--call-sell-wash))' }}>
        <motion.span
          className="absolute -top-1.5 h-6 w-6 -translate-x-1/2 rounded-full border-[3px] border-white bg-[var(--farm-ink)] shadow-md"
          initial={{ left: '50%' }}
          animate={{ left: `${at}%` }}
          transition={{ delay: 0.3, type: 'spring', stiffness: 120, damping: 16 }}
        />
      </div>
      <div className="mt-2 flex justify-between text-[11px] font-bold text-[var(--farm-ink-faint)]">
        <span>{say('supply.low', lang)}</span>
        <span>{say('supply.normal', lang)}</span>
        <span>{say('supply.high', lang)}</span>
      </div>
      {supply.latest_arrivals != null && supply.baseline_arrivals != null && (
        <p className="mt-2.5 text-sm text-[var(--farm-ink-soft)]">
          {say('supply.body', lang, { a: Math.round(supply.latest_arrivals), b: Math.round(supply.baseline_arrivals) })}
        </p>
      )}
    </div>
  );
}
