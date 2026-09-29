'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Lang, translate } from '@/lib/i18n/translations';

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
  /** BCP-47 locale for Web Speech APIs (SpeechRecognition/SpeechSynthesis). */
  speechLocale: string;
}

const SPEECH_LOCALES: Record<Lang, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  kn: 'kn-IN',
};

const STORAGE_KEY = 'mandisense-farm-lang';

const LanguageContext = createContext<LanguageContextValue | null>(null);

/**
 * Language for the farmer surface, persisted across visits.
 *
 * Deliberately separate from the app's theme/personalization store
 * (`useAppStore`): language is a much longer-lived preference than a
 * session's location grant, and keeping it in its own small, focused
 * context means a change here cannot accidentally reset unrelated state.
 */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>('kn');

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY) as Lang | null;
      if (stored === 'en' || stored === 'hi' || stored === 'kn') {
        setLangState(stored);
      }
    } catch {
      // Private-mode or storage-blocked browsers: fall back to the default
      // silently rather than breaking the page over a preference.
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Same as above -- losing the preference is fine, crashing is not.
    }
  }, []);

  const t = useCallback((key: string) => translate(key, lang), [lang]);

  const value = useMemo(
    () => ({ lang, setLang, t, speechLocale: SPEECH_LOCALES[lang] }),
    [lang, setLang, t]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return ctx;
}
