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
      style={{ background: 'rgba(251, 253, 246, 0.92)', backdropFilter: 'blur(12px)' }}
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 lg:max-w-5xl">
        <PlacePicker />
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
