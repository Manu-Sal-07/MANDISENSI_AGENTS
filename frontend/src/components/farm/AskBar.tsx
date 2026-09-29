'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Mic, Search } from 'lucide-react';
import { resolveProduce, produceScript, type ProduceName } from './ProduceIcon';
import ProduceIcon from './ProduceIcon';
import { useLanguage } from '@/context/LanguageContext';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';

/**
 * Asking about a crop.
 *
 * A bare text box assumes the person knows what to type and can type it
 * quickly on a phone keyboard, in a second language, standing up. Most
 * questions here are the same handful, so the crops are offered as tappable
 * produce first and free text second. Tapping a crop asks immediately —
 * one tap to an answer, no keyboard at all.
 */

const CROPS: ProduceName[] = ['tomato', 'onion', 'potato', 'garlic', 'ginger'];

interface AskBarProps {
  onAsk: (question: string) => void;
  isLoading?: boolean;
}

export default function AskBar({ onAsk, isLoading = false }: AskBarProps) {
  const [text, setText] = useState('');
  const { t, lang, speechLocale } = useLanguage();

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const question = text.trim();
    if (question && !isLoading) onAsk(question);
  };

  // A spoken question is asked the moment recognition finishes, rather than
  // dropped into the text box for the farmer to press "Ask" again -- voice
  // exists precisely for someone who would rather not type at all, so
  // requiring a second tap to submit what they just said would defeat it.
  const { isListening, isRecognitionSupported, startListening, stopListening, error } =
    useVoiceAssistant({
      locale: speechLocale,
      onResult: (said) => {
        setText(said);
        if (said.trim() && !isLoading) onAsk(said.trim());
      },
    });

  return (
    <div>
      {/* Crops first: the common case, answered in one tap. */}
      <div className="flex flex-wrap justify-center gap-2.5">
        {CROPS.map((crop) => {
          const produce = resolveProduce(crop);
          const script = produceScript(produce, lang);
          return (
            <button
              key={crop}
              type="button"
              disabled={isLoading}
              onClick={() => onAsk(`Should I sell ${produce.label} today?`)}
              className="farm-focus group flex items-center gap-2 rounded-full border border-[var(--farm-line)] bg-white/85 py-2 pl-2 pr-4 backdrop-blur transition-all hover:border-[var(--farm-line-strong)] hover:bg-white disabled:opacity-50"
            >
              <ProduceIcon name={crop} size="sm" plated={false} />
              <span className="text-left leading-tight">
                <span className="block text-sm font-bold text-[var(--farm-ink)]">
                  {produce.label}
                </span>
                <span className="block text-xs text-[var(--farm-ink-faint)]" lang={script.bcp47}>
                  {script.text}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {/* Free text for everything else. */}
      <form onSubmit={submit} className="mt-4">
        <label htmlFor="ask" className="sr-only">
          Ask about a crop or a mandi
        </label>
        <div className="farm-tap flex items-center gap-2 rounded-2xl border border-[var(--farm-line)] bg-white px-4 shadow-[0_8px_24px_-18px_rgba(42,33,25,0.4)] focus-within:border-[var(--leaf)]">
          <Search className="h-5 w-5 shrink-0 text-[var(--farm-ink-faint)]" />
          <input
            id="ask"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Another crop or mandi"
            disabled={isLoading}
            className="min-w-0 flex-1 bg-transparent py-3 text-base text-[var(--farm-ink)] outline-none placeholder:text-[var(--farm-ink-faint)]"
          />
          {isRecognitionSupported && (
            <button
              type="button"
              onClick={isListening ? stopListening : startListening}
              disabled={isLoading}
              aria-label={isListening ? t('voice.listening') : t('voice.tap_to_speak')}
              className="farm-focus relative shrink-0 rounded-xl p-2.5 transition-colors disabled:opacity-40"
              style={{
                background: isListening ? 'var(--call-sell-wash)' : 'var(--farm-line)',
                color: isListening ? 'var(--call-sell)' : 'var(--farm-ink-soft)',
              }}
            >
              {isListening && (
                <motion.span
                  className="absolute inset-0 rounded-xl"
                  style={{ background: 'var(--call-sell)' }}
                  animate={{ opacity: [0.35, 0, 0.35], scale: [1, 1.35, 1] }}
                  transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                />
              )}
              <Mic className="relative z-10 h-4 w-4" />
            </button>
          )}
          <button
            type="submit"
            disabled={isLoading || !text.trim()}
            className="farm-focus shrink-0 rounded-xl px-4 py-2 text-sm font-bold text-white transition-opacity disabled:opacity-40"
            style={{ background: 'var(--leaf)' }}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-label="Asking" />
            ) : (
              'Ask'
            )}
          </button>
        </div>
        {error === 'not_supported' && (
          <p className="mt-1.5 px-1 text-xs text-[var(--farm-ink-faint)]">{t('voice.not_supported')}</p>
        )}
      </form>
    </div>
  );
}
