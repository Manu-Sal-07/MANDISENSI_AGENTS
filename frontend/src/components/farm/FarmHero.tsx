'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { ChevronDown, TrendingDown, TrendingUp } from 'lucide-react';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { placeName, say, shortDate } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';
import ProduceIcon, { produceScript, resolveProduce } from './ProduceIcon';
import CountUp from './charts/CountUp';

/**
 * Presentation only: the full-bleed dawn poster at the top of the farmer home.
 * Headline, "prices as of" line and the selected crop's price all come from the
 * same copy, catalog and board query the page already uses (the board query key
 * is shared with FieldBoard, so no extra request is made). The greeting comes
 * from the device clock. Layers drift at different rates as the page scrolls.
 */

const GREETING = {
  morning: { en: 'Good morning', kn: 'ಶುಭೋದಯ', hi: 'सुप्रभात' },
  afternoon: { en: 'Good afternoon', kn: 'ಶುಭ ಮಧ್ಯಾಹ್ನ', hi: 'नमस्कार' },
  evening: { en: 'Good evening', kn: 'ಶುಭ ಸಂಜೆ', hi: 'शुभ संध्या' },
} as const;

function partOfDay(hour: number): keyof typeof GREETING {
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

export default function FarmHero({ children }: { children?: React.ReactNode }) {
  const { lang } = useLanguage();
  const { catalog, district, crop } = useFarm();
  const reduce = useReducedMotion();
  const ref = React.useRef<HTMLElement>(null);
  const [part, setPart] = React.useState<keyof typeof GREETING | null>(null);
  React.useEffect(() => setPart(partOfDay(new Date().getHours())), []);

  const { data: board } = useQuery({
    queryKey: ['farm-board', district, crop],
    queryFn: () => farmerApi.board(district, crop),
  });

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const sunY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 140]);
  const farY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 50]);
  const midY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 20]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -50]);
  const fade = useTransform(scrollYProgress, [0, 0.8], [1, reduce ? 1 : 0.15]);

  const ok = board && board.status === 'OK';
  const produce = resolveProduce(crop);
  const cropLabel = produceScript(produce, lang).text;
  const week = ok ? board.changes.d7 : null;

  return (
    <section ref={ref} className="farm-poster relative isolate overflow-hidden">
      {/* sky, sun, far hills */}
      <div className="farm-poster-sky absolute inset-0" aria-hidden="true" />
      <div className="farm-poster-photos absolute inset-0" aria-hidden="true">
        {['farmer-smile', 'mandi-yard', 'vendor-stall', 'seller-turban'].map((n, i) => (
          <span key={n} className="farm-poster-photo" style={{ backgroundImage: `url(/photos/${n}.jpg)`, animationDelay: `${i * 8}s` }} />
        ))}
      </div>
      <div className="farm-poster-scrim absolute inset-0" aria-hidden="true" />
      <div className="farm-poster-stars absolute inset-x-0 top-0 h-2/5" aria-hidden="true" />
      <motion.div style={{ y: sunY }} className="farm-poster-sun" aria-hidden="true" />

      <motion.svg style={{ y: farY }} viewBox="0 0 1440 420" preserveAspectRatio="xMidYMax slice" className="absolute inset-x-0 bottom-0 h-[58%] w-full" aria-hidden="true">
        <path d="M0 210 C180 120 360 190 560 150 C780 108 980 196 1180 140 C1300 108 1390 130 1440 150 V420 H0Z" fill="#2c7a47" opacity="0.55" />
      </motion.svg>
      <motion.svg style={{ y: midY }} viewBox="0 0 1440 420" preserveAspectRatio="xMidYMax slice" className="absolute inset-x-0 bottom-0 h-[46%] w-full" aria-hidden="true">
        <path d="M0 190 C220 130 420 200 660 168 C900 136 1100 206 1440 150 V420 H0Z" fill="#17583a" />
      </motion.svg>

      {/* foreground crop rows, tractor and farmer in silhouette */}
      <svg viewBox="0 0 1440 300" preserveAspectRatio="xMidYMax slice" className="absolute inset-x-0 bottom-0 h-[34%] w-full" aria-hidden="true">
        <path d="M0 80 C260 50 520 96 800 70 C1060 46 1260 90 1440 64 V300 H0Z" fill="#0e3f27" />
        <g className="farm-sway-slow">
          {Array.from({ length: 5 }, (_, row) => (
            <g key={row} opacity={0.65 + row * 0.07}>
              {Array.from({ length: 48 }, (_, i) => {
                const x = (i + row * 0.5) * (1440 / 47) - 14;
                const y = 120 + row * 30;
                const s = 1 + row * 0.28;
                return (
                  <path
                    key={i}
                    d={`M${x} ${y} q ${-7 * s} ${-18 * s} 0 ${-30 * s} q ${7 * s} ${12 * s} 0 ${30 * s}z`}
                    fill={row % 2 ? '#8fd14f' : '#4aa85a'}
                  />
                );
              })}
            </g>
          ))}
        </g>
        <path d="M0 262 C300 248 800 270 1440 252 V300 H0Z" fill="#2a1a10" />
        <g transform="translate(250 92)" fill="#07261a">
          <rect x="30" y="18" width="56" height="30" rx="5" />
          <rect x="58" y="0" width="30" height="22" rx="4" />
          <circle cx="22" cy="54" r="19" /><circle cx="82" cy="60" r="12" />
          <rect x="84" y="-12" width="4" height="14" />
        </g>
        <g transform="translate(1090 40)" fill="#07261a">
          <ellipse cx="22" cy="6" rx="26" ry="6" /><path d="M8 6 C10 -12 34 -12 36 6Z" />
          <circle cx="22" cy="20" r="9" />
          <path d="M8 32 C8 27 36 27 36 32 L40 84 H4Z" />
          <path d="M4 84 H20 L20 104 H8Z M24 84 H40 L36 104 H24Z" />
          <path d="M38 36 L62 18" stroke="#07261a" strokeWidth="6" strokeLinecap="round" />
          <path d="M62 18 L68 -16" stroke="#07261a" strokeWidth="3.5" strokeLinecap="round" />
        </g>
      </svg>
      <div className="farm-poster-mist absolute inset-x-0 bottom-[24%] h-24" aria-hidden="true" />

      {/* content */}
      <motion.div style={{ y: textY, opacity: fade }} className="relative z-10 mx-auto grid w-full max-w-6xl gap-8 px-5 pb-40 pt-10 sm:px-8 sm:pt-14 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-center lg:pb-48 lg:pt-20">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex min-h-[2rem] items-center gap-2 rounded-full bg-[var(--lime)] px-4 py-1.5 text-sm font-extrabold tracking-wide text-[var(--forest)]"
            lang={lang}
          >
            <span className="h-2 w-2 rounded-full bg-[var(--forest)]" aria-hidden="true" />
            {part ? GREETING[part][lang] : '·'}
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="farm-display mt-5 max-w-[15ch] text-[clamp(2.5rem,8.6vw,6.2rem)] font-extrabold leading-[1.08] text-white drop-shadow-[0_4px_30px_rgba(0,30,15,0.45)]"
            lang={lang}
          >
            {say('home.ask', lang)}
          </motion.h1>

          {catalog?.data_through && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-4 inline-flex rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-xs font-bold text-white/90 backdrop-blur-md"
            >
              {say('asof', lang, { d: shortDate(catalog.data_through, lang) })}
            </motion.p>
          )}

          {children && (
            <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.6 }} className="mt-7 max-w-xl">
              {children}
            </motion.div>
          )}
        </div>

        {/* the selected crop as a poster: drawn produce and its recorded price */}
        <div className="hidden lg:block">
          {ok && (
            <motion.div
              key={`${district}-${crop}`}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="relative text-right"
            >
              <span className="farm-float pointer-events-none absolute -right-4 -top-16 opacity-95 drop-shadow-[0_26px_40px_rgba(0,20,10,0.45)]">
                <ProduceIcon name={crop} px={250} plated={false} sway />
              </span>
              <p className="relative pt-44 text-sm font-bold uppercase tracking-[0.16em] text-[var(--lime)]">
                {cropLabel} · {placeName(board.district_name, lang)}
              </p>
              <p className="farm-display relative text-[clamp(3.5rem,8vw,6.5rem)] font-extrabold leading-none text-white drop-shadow-[0_6px_30px_rgba(0,30,15,0.5)]">
                <CountUp value={board.price.value} />
              </p>
              <p className="relative mt-1 flex items-center justify-end gap-3 text-sm font-semibold text-white/80">
                {say('unit.qtl', lang)}
                {week != null && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1 font-bold tabular-nums text-white backdrop-blur-md">
                    {week >= 0 ? <TrendingUp className="h-4 w-4 text-[var(--lime)]" /> : <TrendingDown className="h-4 w-4 text-[#ff9b8f]" />}
                    {Math.abs(week).toFixed(1)}% {say('change.week', lang)}
                  </span>
                )}
              </p>
            </motion.div>
          )}
        </div>
      </motion.div>

      <a href="#destinations" aria-label="Scroll down" className="farm-focus absolute bottom-5 left-1/2 z-10 hidden h-11 w-11 -translate-x-1/2 items-center justify-center rounded-full border border-white/40 bg-white/10 text-white backdrop-blur-md sm:flex">
        <ChevronDown className="h-5 w-5 farm-bob" />
      </a>
    </section>
  );
}
