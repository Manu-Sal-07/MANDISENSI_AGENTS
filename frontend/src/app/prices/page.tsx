'use client';

/**
 * Crop prices: the crop rail, the selected crop's board and the mandi / supply /
 * last-year panels, on a page of their own. The components and data are exactly
 * the ones the farmer home used to carry inline; this page only arranges them.
 */

import React from 'react';
import Link from 'next/link';
import { LineChart, Wallet, Wrench } from 'lucide-react';

import CropRail from '@/components/farm/CropRail';
import FieldBoard, { BoardSide } from '@/components/farm/FieldBoard';
import MandiNav from '@/components/farm/MandiNav';
import PageHero from '@/components/farm/PageHero';
import Reveal from '@/components/farm/Reveal';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { say } from '@/lib/i18n/farmCopy';

const TITLE = { en: 'Crop prices', kn: 'ಬೆಳೆ ಬೆಲೆಗಳು', hi: 'फसल के भाव' } as const;
const SUB = {
  en: 'What your crop is fetching, which mandi pays most, and where the price may go.',
  kn: 'ನಿಮ್ಮ ಬೆಳೆಗೆ ಎಷ್ಟು ಬೆಲೆ, ಯಾವ ಮಂಡಿ ಹೆಚ್ಚು ಕೊಡುತ್ತದೆ, ಮುಂದೆ ಬೆಲೆ ಹೇಗಿರಬಹುದು.',
  hi: 'आपकी फसल का भाव, कौन-सी मंडी सबसे ज़्यादा देती है, और भाव आगे कहाँ जा सकता है।',
} as const;
const ERR = {
  en: 'Cannot reach the mandi records right now. Try again in a moment.',
  kn: 'ಮಾರುಕಟ್ಟೆ ದಾಖಲೆಗಳಿಗೆ ಸಂಪರ್ಕ ಸಿಗುತ್ತಿಲ್ಲ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.',
  hi: 'मंडी रिकॉर्ड से संपर्क नहीं हो पा रहा। थोड़ी देर बाद कोशिश करें।',
} as const;

export default function PricesPage() {
  const { lang } = useLanguage();
  const { catalogError } = useFarm();

  return (
    <div className="farm-surface min-h-screen pb-28 md:pb-16">
      <MandiNav />
      <main className="mx-auto max-w-3xl px-4 pb-10 pt-6 lg:max-w-6xl">
        <PageHero
          photo="mandi-yard"
          title={TITLE[lang]}
          subtitle={SUB[lang]}
          icon={<LineChart className="h-7 w-7" />}
          produce={['tomato', 'onion', 'potato']}
        />

        {catalogError && (
          <p role="alert" className="mt-5 rounded-2xl bg-[var(--call-sell-wash)] p-4 text-sm font-semibold text-[var(--call-sell)]">
            {ERR[lang]}
          </p>
        )}

        <div className="mt-6">
          <CropRail />
        </div>

        <div id="field-board" className="mt-6 scroll-mt-32 lg:grid lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:items-start lg:gap-8">
          <Reveal>
            <FieldBoard />
            <div className="mt-5 grid grid-cols-[1fr_auto] gap-3">
              <Link
                href="/sell-plan"
                className="farm-focus flex items-center justify-center gap-3 rounded-2xl bg-[var(--leaf)] px-6 py-4 shadow-[0_16px_36px_-18px_rgba(19,92,46,0.7)] transition-transform hover:-translate-y-0.5 active:scale-[0.99]"
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
            </div>
          </Reveal>

          <Reveal delay={0.12} className="mt-6 lg:mt-0">
            <BoardSide />
          </Reveal>
        </div>
      </main>
    </div>
  );
}
