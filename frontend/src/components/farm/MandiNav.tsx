'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { MapPin, Store } from 'lucide-react';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { placeName, rupees, say } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

/**
 * A sticky strip of every mandi for the selected crop, so a farmer can jump to
 * any mandi's page without scrolling to the list below. It reads the same board
 * query as the field board (shared cache, no extra request) and links to the
 * existing /mandi/[id] route. Mandis in the farmer's own district come first.
 */
export default function MandiNav() {
  const { district, crop } = useFarm();
  const { lang } = useLanguage();
  const { data: board } = useQuery({
    queryKey: ['farm-board', district, crop],
    queryFn: () => farmerApi.board(district, crop),
  });
  if (!board || board.status !== 'OK' || !board.mandis.length) return null;

  const mandis = [...board.mandis].sort((a, b) => Number(b.in_district) - Number(a.in_district));

  return (
    <nav aria-label={say('mandis.title', lang)} className="farm-mandinav sticky top-[68px] z-40">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:px-8">
        <span className="hidden shrink-0 items-center gap-2 rounded-full bg-[var(--lime)] px-3.5 py-2 text-xs font-extrabold uppercase tracking-wider text-[var(--forest)] sm:flex">
          <Store className="h-4 w-4" />
          {say('mandis.title', lang)}
        </span>
        <ul key={`${district}-${crop}`} className="farm-mandinav-scroll no-scrollbar flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
          {mandis.map((m, i) => (
            <motion.li
              key={m.id}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.05 * i, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className="shrink-0"
            >
              <Link
                href={`/mandi/${m.id}`}
                className={`farm-focus farm-mandichip group flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-bold ${
                  m.in_district ? 'border-[var(--lime)]/70 bg-[var(--lime)]/15 text-white' : 'border-white/20 bg-white/10 text-white/90'
                }`}
              >
                <MapPin className={`h-3.5 w-3.5 ${m.in_district ? 'text-[var(--lime)]' : 'text-white/60'}`} />
                <span className="max-w-[10rem] truncate">{placeName(m, lang)}</span>
                <span className="tabular-nums text-[var(--lime)]">{rupees(m.price)}</span>
              </Link>
            </motion.li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
