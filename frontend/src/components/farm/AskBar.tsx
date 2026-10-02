'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Mic, Search } from 'lucide-react';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';
import { say } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

/**
 * Ask by typing or by voice: "tomato in Kolar". The crop and place named in
 * the question become the selection, and the board below answers. A spoken
 * question is sent the moment recognition finishes — a person who chose voice
 * to avoid typing should not have to press anything afterwards.
 */
export default function AskBar() {
  const router = useRouter();
  const { district, setDistrict, setCrop, catalog } = useFarm();
  const { lang, speechLocale } = useLanguage();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  // Speech support is only knowable in the browser; rendering the mic before
  // mount keeps the server and client HTML identical.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setNote(null);
    try {
      const r = await farmerApi.ask(q, district);
      if (!r.understood || !r.crop) {
        setNote(say('ask.notfound', lang));
        return;
      }
      if (r.district && catalog?.districts.some((d) => d.id === r.district && d.crops.some((c) => c.crop === r.crop))) {
        setDistrict(r.district);
      }
      setCrop(r.crop);
      const board = document.getElementById('field-board');
      if (board) board.scrollIntoView({ behavior: 'smooth', block: 'start' });
      else router.push('/prices');
    } catch {
      setNote(say('ask.notfound', lang));
    } finally {
      setBusy(false);
    }
  };

  const { isListening, isRecognitionSupported, startListening, stopListening } = useVoiceAssistant({
    locale: speechLocale,
    onResult: (said) => {
      setText(said);
      ask(said);
    },
  });

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(text);
        }}
        className="flex items-center gap-2 rounded-2xl border border-[var(--farm-line-strong)] bg-white px-3 py-2 shadow-[0_10px_26px_-18px_rgba(42,33,25,0.5)] focus-within:border-[var(--leaf)]"
      >
        <Search className="h-5 w-5 shrink-0 text-[var(--farm-ink-faint)]" />
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={say('ask.placeholder', lang)}
          aria-label={say('ask.placeholder', lang)}
          className="min-w-0 flex-1 bg-transparent py-2 text-base text-[var(--farm-ink)] outline-none placeholder:text-[var(--farm-ink-faint)]"
        />
        {mounted && isRecognitionSupported && (
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            aria-label="Speak"
            className="farm-focus flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
            style={{ background: isListening ? 'var(--call-sell-wash)' : 'var(--farm-paper-warm)', color: isListening ? 'var(--call-sell)' : 'var(--farm-ink-soft)' }}
          >
            <Mic className={`h-[18px] w-[18px] ${isListening ? 'animate-pulse' : ''}`} />
          </button>
        )}
        <button type="submit" disabled={busy || !text.trim()} className="farm-focus flex h-10 shrink-0 items-center rounded-full bg-[var(--leaf)] px-4 text-sm font-bold text-white disabled:opacity-50">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : lang === 'kn' ? 'ಕೇಳಿ' : lang === 'hi' ? 'पूछें' : 'Ask'}
        </button>
      </form>
      {note && <p role="status" className="mt-2 px-1 text-sm font-semibold text-[var(--call-sell)]">{note}</p>}
    </div>
  );
}
