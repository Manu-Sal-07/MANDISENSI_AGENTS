'use client';

/**
 * One mandi, every crop it reported lately — with what sellers actually got.
 *
 * Reached from a row on the home page when the question has narrowed to "is it
 * worth taking a load to this market?". Each crop shows the typical price, the
 * lowest and highest paid that day, how much arrived, and the week's change.
 */

import PageHero from '@/components/farm/PageHero';
import React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ChevronLeft, Store, Truck } from 'lucide-react';

import ProduceIcon, { produceScript, resolveProduce } from '@/components/farm/ProduceIcon';
import UnavailableNotice from '@/components/farm/tools/UnavailableNotice';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { placeName, rupees, say, shortDate, tri } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

export default function MandiPageRoute() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { lang } = useLanguage();
  const { setMandi, setCrop, setDistrict } = useFarm();
  const { data, isLoading } = useQuery({ queryKey: ['farm-mandi', id], queryFn: () => farmerApi.mandi(id) });

  const plan = (crop: string) => {
    if (!data?.mandi) return;
    setDistrict(data.mandi.district);
    setCrop(crop as never);
    setMandi(data.mandi.id);
    router.push('/sell-plan');
  };

  const all = data?.crops ?? [];

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-2xl px-4 pb-10 pt-6 lg:max-w-3xl">
        <button type="button" onClick={() => router.back()} className="farm-focus -ml-1 mb-3 flex items-center gap-1 rounded-lg px-1 py-1 text-sm font-bold text-[var(--farm-ink-soft)]">
          <ChevronLeft className="h-4 w-4" /> {tri(lang, 'Back', 'ಹಿಂದೆ', 'वापस')}
        </button>

        {isLoading && <div className="farm-card h-40 animate-pulse bg-white/70" />}
        {data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {data?.status === 'OK' && data.mandi && (
          <>
            <PageHero photo="mandi-yard"
              title={placeName(data.mandi, lang)}
              subtitle={tri(lang, 'What each crop fetched at the latest sale', 'ಇತ್ತೀಚಿನ ವ್ಯಾಪಾರದಲ್ಲಿ ಪ್ರತಿ ಬೆಳೆಗೆ ಸಿಕ್ಕಿದ್ದು', 'ताज़ा बिक्री में हर फसल का भाव')}
              icon={<Store className="h-7 w-7" />}
              tone="soil"
              produce={['tomato', 'onion', 'potato']}
            />

            <ul className="mt-5 space-y-3">
              {all.map((c, i) => {
                const up = (c.d7 ?? 0) >= 0;
                const span = c.max - c.min || 1;
                return (
                  <motion.li key={c.crop} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }} className="farm-row p-4">
                    <div className="flex items-center gap-3">
                      <ProduceIcon name={c.crop} size="md" />
                      <div className="min-w-0 flex-1">
                        <p className="text-base font-bold text-[var(--farm-ink)]">{produceScript(resolveProduce(c.crop), lang).text}</p>
                        <p className="text-xs text-[var(--farm-ink-faint)]">{shortDate(c.date, lang)} · {say('mandis.tonnes', lang, { n: c.arrivals })}</p>
                      </div>
                      <div className="text-right">
                        <p className="farm-display text-2xl tabular-nums text-[var(--farm-ink)]">{rupees(c.price)}</p>
                        {c.d7 != null && (
                          <p className="text-xs font-bold tabular-nums" style={{ color: up ? 'var(--leaf-deep)' : 'var(--call-sell)' }}>
                            {up ? '▲' : '▼'} {Math.abs(c.d7).toFixed(1)}% {say('change.week', lang)}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="relative mt-3 h-2.5 rounded-full bg-[var(--farm-line)]">
                      <span className="absolute inset-y-0 left-0 right-0 rounded-full" style={{ background: 'color-mix(in srgb, var(--leaf) 38%, white)' }} />
                      <span className="absolute -top-1 h-[18px] w-1 -translate-x-1/2 rounded-full bg-[var(--farm-ink)]" style={{ left: `${((c.price - c.min) / span) * 100}%` }} />
                    </div>
                    <div className="mt-1.5 flex justify-between text-xs tabular-nums text-[var(--farm-ink-faint)]">
                      <span>{rupees(c.min)}</span>
                      <span>{rupees(c.max)}</span>
                    </div>
                    <button type="button" onClick={() => plan(c.crop)} className="farm-focus mt-3 flex items-center gap-1.5 rounded-lg text-sm font-bold text-[var(--leaf)]">
                      <Truck className="h-4 w-4" /> {say('plan.cta', lang)}
                    </button>
                  </motion.li>
                );
              })}
            </ul>
            <Link href="/" className="farm-focus mt-6 inline-block rounded-lg text-sm font-bold text-[var(--farm-ink-soft)] underline underline-offset-4">
              {tri(lang, 'Back to my crops', 'ನನ್ನ ಬೆಳೆಗಳಿಗೆ ಹಿಂತಿರುಗಿ', 'मेरी फसलों पर लौटें')}
            </Link>
          </>
        )}
      </main>
    </div>
  );
}
