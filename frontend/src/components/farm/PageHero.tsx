'use client';

import React from 'react';
import { motion } from 'framer-motion';

import ProduceIcon from './ProduceIcon';

/**
 * The banner at the top of every inner farmer page: a tinted sunrise panel
 * with the page's icon, its title, a one-line purpose, and a cluster of drawn
 * produce. Presentation only; callers pass the text they already rendered.
 */
export default function PageHero({
  title,
  subtitle,
  icon,
  produce = ['tomato', 'onion', 'potato'],
  tone = 'leaf',
  photo = 'vendor-stall',
  children,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  produce?: string[];
  tone?: 'leaf' | 'turmeric' | 'soil';
  photo?: 'mandi-yard' | 'vendor-stall' | 'farmer-smile' | 'seller-turban';
  children?: React.ReactNode;
}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={`farm-pagehero farm-pagehero-${tone} relative overflow-hidden rounded-[1.75rem] border border-[var(--farm-line)] px-5 py-7 sm:px-8 sm:py-10`}
    >
      <div className="farm-pagehero-photo" style={{ backgroundImage: `url(/photos/${photo}.jpg)` }} aria-hidden="true" />
      <div className="farm-pagehero-glow" aria-hidden="true" />
      <div className="relative z-10 flex items-center gap-4">
        {icon && (
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[var(--lime)] text-[var(--forest)] shadow-[0_10px_28px_-10px_rgba(200,240,76,0.7)]">
            {icon}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="farm-display text-[1.75rem] leading-tight text-white sm:text-5xl">{title}</h1>
          {subtitle && <div className="mt-1 max-w-[56ch] text-[15px] leading-snug text-white/80">{subtitle}</div>}
        </div>
        <div className="relative hidden h-20 w-28 shrink-0 sm:block" aria-hidden="true">
          {produce.slice(0, 3).map((p, i) => (
            <span key={p} className="farm-float absolute" style={{ left: i * 26, top: i === 1 ? 0 : 18, animationDelay: `${i * -1.7}s` }}>
              <ProduceIcon name={p} px={i === 1 ? 56 : 46} />
            </span>
          ))}
        </div>
      </div>
      {children && <div className="relative z-10 mt-4">{children}</div>}
    </motion.header>
  );
}
