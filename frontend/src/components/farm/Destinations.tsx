'use client';

import React from 'react';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, LineChart, PiggyBank, Wallet, Wrench } from 'lucide-react';

import { useLanguage } from '@/context/LanguageContext';
import { say } from '@/lib/i18n/farmCopy';

const PRICES = {
  title: { en: 'Crop prices', kn: 'ಬೆಳೆ ಬೆಲೆಗಳು', hi: 'फसल के भाव' },
  sub: { en: 'Price, mandis and outlook for every crop', kn: 'ಪ್ರತಿ ಬೆಳೆಯ ಬೆಲೆ, ಮಂಡಿ, ಮುನ್ನೋಟ', hi: 'हर फसल का भाव, मंडी और अनुमान' },
} as const;

/**
 * The launchpad on the farmer home: four big photo cards, one per destination.
 * Presentation only; every card is a plain link to an existing route.
 */
export default function Destinations() {
  const { lang, t } = useLanguage();
  const reduce = useReducedMotion();

  const cards = [
    { href: '/prices', photo: 'mandi-yard', icon: LineChart, title: PRICES.title[lang], sub: PRICES.sub[lang] },
    { href: '/sell-plan', photo: 'vendor-stall', icon: Wallet, title: say('plan.cta', lang), sub: t('sellplan.subtitle') },
    { href: '/my-money', photo: 'seller-turban', icon: PiggyBank, title: t('nav.my_money'), sub: t('mymoney.subtitle') },
    { href: '/tools', photo: 'farmer-smile', icon: Wrench, title: t('nav.tools'), sub: t('tools.subtitle') },
  ];

  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <motion.li
            key={c.href}
            initial={reduce ? false : { opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.6, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link href={c.href} className="farm-dest farm-focus group relative block overflow-hidden rounded-[1.75rem]">
              <span className="farm-dest-img" style={{ backgroundImage: `url(/photos/${c.photo}.jpg)` }} aria-hidden="true" />
              <span className="farm-dest-scrim" aria-hidden="true" />
              <span className="relative z-10 flex min-h-[13rem] flex-col justify-between p-5 sm:min-h-[15rem] sm:p-6">
                <span className="flex items-start justify-between">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--lime)] text-[var(--forest)]">
                    <Icon className="h-6 w-6" />
                  </span>
                  <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/40 text-white transition-all group-hover:border-[var(--lime)] group-hover:bg-[var(--lime)] group-hover:text-[var(--forest)]">
                    <ArrowUpRight className="h-5 w-5" />
                  </span>
                </span>
                <span>
                  <span className="farm-display block text-2xl font-extrabold leading-tight text-white sm:text-3xl">{c.title}</span>
                  <span className="mt-1 block max-w-[34ch] text-sm leading-snug text-white/80">{c.sub}</span>
                </span>
              </span>
            </Link>
          </motion.li>
        );
      })}
    </ul>
  );
}
