'use client';

/**
 * Trader Tools hub: the eight tools as photo cards in three groups. Each tool
 * lives on its own page; the commodity / mandi focus is shared between them.
 */

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowUpRight, Wrench } from 'lucide-react';

import DeskHero from '@/components/trader/DeskHero';
import { TOOL_GROUPS, TRADER_TOOLS } from '@/lib/traderTools';

const GROUP_NOTE: Record<(typeof TOOL_GROUPS)[number], string> = {
  'Market scan': 'Where the money is moving between mandis, districts and crops.',
  'Risk and regime': 'How turbulent the market is, and what that has meant before.',
  Forecasting: 'Precedent and a calibrated forward range for your horizon.',
};

export default function TraderToolsHub() {
  return (
    <div className="tb-clear min-h-screen pb-28 md:pb-20">
      <div className="mx-auto max-w-[1280px] px-4 pt-8 sm:px-6">
        <DeskHero
          kicker="Trader Tools"
          title="Trader Tools"
          subtitle="Eight focused tools for spreads, volatility, precedent, scenarios, forward pricing, position risk and cross-commodity transmission. Pick one."
          icon={<Wrench className="h-7 w-7" />}
          accent="amber"
          photo="desk-scale"
        />

        {TOOL_GROUPS.map((group) => (
          <section key={group} className="mt-10">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-display text-xl font-black tracking-tight text-foreground">{group}</h2>
              <p className="text-sm text-neutral-signal">{GROUP_NOTE[group]}</p>
            </div>
            <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {TRADER_TOOLS.filter((t) => t.group === group).map((t, i) => {
                const Icon = t.icon;
                return (
                  <motion.li
                    key={t.slug}
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-40px' }}
                    transition={{ duration: 0.5, delay: i * 0.07, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <Link href={t.href} className={`tb-module tb-accent-${t.accent} farm-focus group relative block h-full overflow-hidden rounded-3xl`}>
                      <span className="tb-module-img" style={{ backgroundImage: `url(/photos/${t.photo}.jpg)` }} aria-hidden="true" />
                      <span className="tb-module-scrim" aria-hidden="true" />
                      <span className="relative z-10 flex min-h-[14rem] flex-col justify-between p-5 sm:p-6">
                        <span className="flex items-start justify-between">
                          <span className="tb-hero-icon tb-icon-solid flex h-12 w-12 items-center justify-center rounded-2xl">
                            <Icon className="h-6 w-6" />
                          </span>
                          <span className="tb-arrow flex h-10 w-10 items-center justify-center rounded-full">
                            <ArrowUpRight className="h-5 w-5" />
                          </span>
                        </span>
                        <span>
                          <span className="font-display block text-xl font-black leading-tight tracking-tight text-white sm:text-2xl">{t.title}</span>
                          <span className="mt-1.5 block text-sm leading-relaxed text-white/80">{t.blurb}</span>
                        </span>
                      </span>
                    </Link>
                  </motion.li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
