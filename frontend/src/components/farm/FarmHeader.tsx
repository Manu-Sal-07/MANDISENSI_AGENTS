'use client';

import { useLanguage } from '@/context/LanguageContext';
import { LANGUAGE_LABELS, type Lang } from '@/lib/i18n/translations';
import PlacePicker from './PlacePicker';

const LANGUAGE_CYCLE: Lang[] = ['kn', 'hi', 'en'];

/**
 * Header for the farmer surface.
 *
 * There is no brand bar and no product navigation: the only two things a
 * farmer needs at the top of every screen are *whose prices am I looking at*
 * (the district) and *in which language*. Both are real buttons, sized for a
 * thumb used outdoors.
 */
export default function FarmHeader() {
  const { lang, setLang } = useLanguage();

  const cycleLanguage = () => {
    setLang(LANGUAGE_CYCLE[(LANGUAGE_CYCLE.indexOf(lang) + 1) % LANGUAGE_CYCLE.length]);
  };

  return (
    <header
      className="sticky top-0 z-50 border-b border-[var(--farm-line)]"
      style={{ background: 'rgba(255, 249, 226, 0.78)', backdropFilter: 'blur(14px) saturate(1.3)', WebkitBackdropFilter: 'blur(14px) saturate(1.3)' }}
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 lg:max-w-5xl">
        <div className="flex min-w-0 items-center gap-2.5">
          <span aria-hidden="true" className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--leaf)] shadow-[0_8px_18px_-8px_rgba(19,92,46,0.8)] min-[400px]:flex">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
              <path d="M5 19C5 9 11 4 20 4c0 9-5 15-13 15-.7 0-1.4 0-2 0z" fill="#fff" fillOpacity="0.95" />
              <path d="M6 18C9 14 12 11 16 8" stroke="#1b7a3e" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </span>
          <PlacePicker />
        </div>
        <button
          onClick={cycleLanguage}
          aria-label="Change language"
          className="farm-focus shrink-0 rounded-xl border border-[var(--farm-line)] bg-white px-3.5 py-2.5 text-sm font-bold text-[var(--farm-ink)] transition-colors hover:border-[var(--leaf)]"
        >
          {LANGUAGE_LABELS[lang]}
        </button>
      </div>
    </header>
  );
}
