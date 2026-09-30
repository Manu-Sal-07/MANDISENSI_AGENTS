'use client';

/**
 * Farmer home.
 *
 * One question, answered with recorded prices: what is my crop worth today, and
 * is it worth waiting? Everything is arranged from that. The crop rail picks the
 * crop, the field board answers for it, and the panels beside it say where the
 * price is best today and why it might move. The record of how often we have been
 * right is on the same page as the advice, not behind a link.
 *
 * The page runs entirely on real recorded Agmarknet prices (see the farmer data
 * world in `mandisense_ai/farmer/world.py`); the trader screens are separate and
 * are not read here.
 */

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Wallet, Wrench } from 'lucide-react';

import AskBar from '@/components/farm/AskBar';
import CropRail from '@/components/farm/CropRail';
import FieldBoard, { BoardSide } from '@/components/farm/FieldBoard';
import TrustGrid from '@/components/farm/TrustGrid';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { say, shortDate } from '@/lib/i18n/farmCopy';

const EASE = [0.16, 1, 0.3, 1] as const;

export default function FarmerHome() {
  const { lang } = useLanguage();
  const { catalog, catalogError } = useFarm();

  return (
    <div className="farm-surface relative min-h-screen pb-28 md:pb-16">
      <div className="mx-auto w-full max-w-3xl px-4 pt-7 lg:max-w-5xl">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE }}>
          <h1 className="farm-display text-[1.9rem] leading-tight text-[var(--farm-ink)] sm:text-4xl" lang={lang}>
            {say('home.ask', lang)}
          </h1>
          {catalog?.data_through && (
            <p className="mt-1 text-sm text-[var(--farm-ink-faint)]">{say('asof', lang, { d: shortDate(catalog.data_through, lang) })}</p>
          )}
        </motion.div>

        <div className="mt-5">
          <AskBar />
        </div>

        {catalogError && (
          <p role="alert" className="mt-5 rounded-2xl bg-[var(--call-sell-wash)] p-4 text-sm font-semibold text-[var(--call-sell)]">
            {lang === 'kn' ? 'ಮಾರುಕಟ್ಟೆ ದಾಖಲೆಗಳಿಗೆ ಸಂಪರ್ಕ ಸಿಗುತ್ತಿಲ್ಲ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.' : lang === 'hi' ? 'मंडी रिकॉर्ड से संपर्क नहीं हो पा रहा। थोड़ी देर बाद कोशिश करें।' : 'Cannot reach the mandi records right now. Try again in a moment.'}
          </p>
        )}

        <div className="mt-6">
          <CropRail />
        </div>

        <div id="field-board" className="mt-6 scroll-mt-24 lg:grid lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:items-start lg:gap-7">
          <div>
            <FieldBoard />
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mt-5 grid grid-cols-[1fr_auto] gap-3">
              <Link
                href="/sell-plan"
                className="farm-focus flex items-center justify-center gap-3 rounded-2xl bg-[var(--leaf)] px-6 py-4 shadow-[0_16px_36px_-18px_rgba(19,92,46,0.7)] transition-transform active:scale-[0.99]"
              >
                <Wallet className="h-5 w-5 shrink-0 text-white" />
                <span className="farm-display text-lg text-white">{say('plan.cta', lang)}</span>
              </Link>
              <Link
                href="/tools"
                aria-label={say('more.tools', lang)}
                className="farm-focus flex items-center justify-center rounded-2xl border border-[var(--farm-line-strong)] bg-white px-5 text-[var(--farm-ink-soft)] hover:border-[var(--leaf)] hover:text-[var(--leaf)]"
              >
                <Wrench className="h-5 w-5" />
              </Link>
            </motion.div>
          </div>

          <div className="mt-6 lg:mt-0">
            <BoardSide />
          </div>
        </div>

        <div className="mt-8">
          <TrustGrid />
        </div>

        <footer className="mx-auto mt-12 max-w-2xl pb-4 text-center">
          <p className="text-sm text-[var(--farm-ink-faint)]">
            {lang === 'kn'
              ? 'ಬೆಲೆಗಳು ಸರ್ಕಾರಿ ಮಂಡಿ ದಾಖಲೆಗಳಿಂದ ಬಂದಿವೆ. ಸಲಹೆ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಖಾತರಿಯಲ್ಲ.'
              : lang === 'hi'
                ? 'भाव सरकारी मंडी रिकॉर्ड से लिए गए हैं। सलाह मार्गदर्शन है, गारंटी नहीं।'
                : 'Prices come from government mandi records. Advice is guidance, not a guarantee.'}
          </p>
        </footer>
      </div>
    </div>
  );
}
