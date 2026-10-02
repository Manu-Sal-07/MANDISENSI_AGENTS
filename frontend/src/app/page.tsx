'use client';

/**
 * Farmer home.
 *
 * The front door: a dawn poster that asks the one question (what is my crop
 * worth today?), the looping price ticker, a sticky strip of mandis, the crop
 * rail that picks the crop shown on the poster, and a launchpad into the
 * dedicated pages: crop prices (/prices), sale planner, my money and tools.
 * The detailed price board, mandi list and supply panels live on /prices.
 *
 * The page runs entirely on real recorded Agmarknet prices (see the farmer data
 * world in `mandisense_ai/farmer/world.py`); the trader screens are separate and
 * are not read here.
 */

import React from 'react';

import AskBar from '@/components/farm/AskBar';
import CropRail from '@/components/farm/CropRail';
import Destinations from '@/components/farm/Destinations';
import FarmHero from '@/components/farm/FarmHero';
import MandiNav from '@/components/farm/MandiNav';
import PriceTicker from '@/components/farm/PriceTicker';
import Reveal from '@/components/farm/Reveal';
import TrustGrid from '@/components/farm/TrustGrid';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';

export default function FarmerHome() {
  const { lang } = useLanguage();
  const { catalogError } = useFarm();

  return (
    <div className="farm-surface relative min-h-screen pb-24 md:pb-0">
      <FarmHero>
        <AskBar />
      </FarmHero>
      <PriceTicker />
      <MandiNav />

      {catalogError && (
        <p role="alert" className="mx-auto mt-5 max-w-3xl rounded-2xl bg-[var(--call-sell-wash)] p-4 text-sm font-semibold text-[var(--call-sell)]">
          {lang === 'kn' ? 'ಮಾರುಕಟ್ಟೆ ದಾಖಲೆಗಳಿಗೆ ಸಂಪರ್ಕ ಸಿಗುತ್ತಿಲ್ಲ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.' : lang === 'hi' ? 'मंडी रिकॉर्ड से संपर्क नहीं हो पा रहा। थोड़ी देर बाद कोशिश करें।' : 'Cannot reach the mandi records right now. Try again in a moment.'}
        </p>
      )}

      {/* dark band: pick a crop, then go where you need to */}
      <section id="destinations" className="farm-band-dark scroll-mt-32">
        <div className="mx-auto w-full max-w-3xl px-4 py-10 lg:max-w-6xl lg:py-16">
          <Reveal>
            <CropRail />
          </Reveal>
          <div className="mt-8">
            <Destinations />
          </div>
        </div>
      </section>

      {/* light band: how often we have been right */}
      <section className="farm-band-light">
        <div className="mx-auto w-full max-w-3xl px-4 py-12 lg:max-w-5xl lg:py-16">
          <Reveal>
            <TrustGrid />
          </Reveal>

          <footer className="mx-auto mt-12 max-w-2xl pb-6 text-center">
            <p className="text-sm text-[var(--farm-ink-soft)]">
              {lang === 'kn'
                ? 'ಬೆಲೆಗಳು ಸರ್ಕಾರಿ ಮಂಡಿ ದಾಖಲೆಗಳಿಂದ ಬಂದಿವೆ. ಸಲಹೆ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಖಾತರಿಯಲ್ಲ.'
                : lang === 'hi'
                  ? 'भाव सरकारी मंडी रिकॉर्ड से लिए गए हैं। सलाह मार्गदर्शन है, गारंटी नहीं।'
                  : 'Prices come from government mandi records. Advice is guidance, not a guarantee.'}
            </p>
            <p className="mt-3 text-xs text-[var(--farm-ink-faint)]">
              Photos via Wikimedia Commons: Mananshah1008 (CC BY-SA 3.0), Avinash Singh (CC BY-SA 4.0), amanjeev (CC BY-SA 3.0), Bitter Honey Clicks (CC BY-SA 4.0).
            </p>
          </footer>
        </div>
      </section>
    </div>
  );
}
