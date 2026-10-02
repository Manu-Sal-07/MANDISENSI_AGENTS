'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { MapPin } from 'lucide-react';

import { useLanguage } from '@/context/LanguageContext';
import { placeName, rupees, say } from '@/lib/i18n/farmCopy';
import type { MandiToday } from '@/services/farmerApi';

/**
 * What each mandi paid today, as a bar from the lowest to the highest price
 * anyone got, with a tick at the typical price.
 *
 * The range is the point. A farmer told "₹1,460 at Kolar" learns one number;
 * shown that some sellers got ₹400 and some ₹3,330, they learn how much their
 * grade and their bargaining matter. All rows share one scale so they can be
 * compared by eye.
 */
export default function MandiBoard({ mandis }: { mandis: MandiToday[] }) {
  const { lang } = useLanguage();

  if (!mandis.length) {
    return <p className="rounded-2xl bg-[var(--farm-paper-warm)] p-5 text-sm text-[var(--farm-ink-soft)]">{say('mandis.empty', lang)}</p>;
  }

  const lo = Math.min(...mandis.map((m) => m.min));
  const hi = Math.max(...mandis.map((m) => m.max));
  const span = hi - lo || 1;
  const pos = (v: number) => `${((v - lo) / span) * 100}%`;
  // "Best" only among mandis that took real volume: a price on two crates is
  // a headline, not a market.
  // and a price far above what the other markets paid is usually a different
  // grade, so neither earns the badge.
  const liquid = mandis.filter((m) => m.arrivals >= 1);
  const sorted = [...liquid].map((m) => m.price).sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  const credible = liquid.filter((m) => m.price <= median * 1.5);
  const best = credible.length ? credible.reduce((a, b) => (b.price > a.price ? b : a)) : null;

  const groups = [
    { title: say('mandis.here', lang), rows: mandis.filter((m) => m.in_district) },
    { title: say('mandis.elsewhere', lang), rows: mandis.filter((m) => !m.in_district) },
  ].filter((g) => g.rows.length);

  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <div key={group.title}>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-bold text-[var(--farm-ink-faint)]">
            <MapPin className="h-3.5 w-3.5" /> {group.title}
          </p>
          <ul className="divide-y divide-[var(--farm-line)]">
            {group.rows.map((m, i) => (
              <li key={m.id} className="py-3.5">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="min-w-0 truncate text-base font-bold text-[var(--farm-ink)]">
                    <Link href={`/mandi/${m.id}`} className="farm-focus rounded hover:underline">{placeName(m, lang)}</Link>
                    {best?.id === m.id && (
                      <span className="ml-2 rounded-full bg-[var(--leaf-wash)] px-2 py-0.5 align-middle text-[11px] font-bold text-[var(--leaf-deep)]">
                        ★ {lang === 'kn' ? 'ಅತ್ಯುತ್ತಮ' : lang === 'hi' ? 'सबसे अच्छा' : 'Best'}
                      </span>
                    )}
                  </p>
                  <p className="farm-display shrink-0 text-xl tabular-nums text-[var(--farm-ink)]">{rupees(m.price)}</p>
                </div>

                <div className="relative mt-2.5 h-2.5 rounded-full bg-[var(--farm-line)]">
                  <motion.span
                    className="absolute inset-y-0 rounded-full"
                    style={{ left: pos(m.min), background: 'color-mix(in srgb, var(--leaf) 38%, white)' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${((m.max - m.min) / span) * 100}%` }}
                    transition={{ delay: 0.15 + i * 0.05, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  />
                  <span
                    className="absolute -top-1 h-4.5 w-1 -translate-x-1/2 rounded-full bg-[var(--farm-ink)]"
                    style={{ left: pos(m.price), height: 18 }}
                    aria-hidden="true"
                  />
                </div>

                <div className="mt-1.5 flex items-center justify-between text-xs tabular-nums text-[var(--farm-ink-faint)]">
                  <span>{rupees(m.min)} – {rupees(m.max)}</span>
                  <span>{say('mandis.tonnes', lang, { n: m.arrivals })}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
