'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion, useReducedMotion } from 'framer-motion';

import { useLanguage } from '@/context/LanguageContext';
import { say } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

/**
 * "How often have we been right?" as a hundred dots.
 *
 * Sixty-one filled dots read at a glance without any sense of percentages, and
 * the empty ones are just as visible as the full ones: the misses are part of
 * the picture. The figure is measured on weeks the model never trained on.
 */
export default function TrustGrid() {
  const { lang } = useLanguage();
  const reduce = useReducedMotion();
  const { data } = useQuery({ queryKey: ['farm-accuracy'], queryFn: () => farmerApi.accuracy(), staleTime: 30 * 60 * 1000 });

  const right = data?.overall?.direction_right;
  if (!data?.available || right == null) return null;
  const filled = Math.round(right * 100);

  return (
    <section className="farm-section farm-section-warm">
      <div className="grid gap-6 sm:grid-cols-[auto_1fr] sm:items-center">
        <div
          className="grid w-fit gap-[5px]"
          style={{ gridTemplateColumns: 'repeat(10, 1fr)' }}
          role="img"
          aria-label={say('trust.body', lang, { n: filled })}
        >
          {Array.from({ length: 100 }, (_, i) => (
            <motion.span
              key={i}
              className="block h-[14px] w-[14px] rounded-full sm:h-4 sm:w-4"
              style={{ background: i < filled ? 'var(--leaf)' : 'var(--farm-line-strong)' }}
              initial={reduce ? false : { scale: 0, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: i * 0.007, duration: 0.25 }}
            />
          ))}
        </div>

        <div>
          <h2 className="farm-display text-2xl text-[var(--farm-ink)]">{say('trust.title', lang)}</h2>
          <p className="mt-2 max-w-[44ch] text-[15px] leading-relaxed text-[var(--farm-ink)]">{say('trust.body', lang, { n: filled })}</p>
          <p className="mt-2 max-w-[44ch] text-sm leading-relaxed text-[var(--farm-ink-soft)]">{say('trust.honest', lang)}</p>
          <Link href="/accuracy" className="farm-focus mt-3 inline-block rounded-lg text-sm font-bold text-[var(--leaf)] underline decoration-2 underline-offset-4">
            {say('trust.more', lang)}
          </Link>
        </div>
      </div>
    </section>
  );
}
