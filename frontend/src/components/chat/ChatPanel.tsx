'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { AlertTriangle, Check, ExternalLink, Globe2, Loader2, Mic, RotateCcw, Send, Sparkles, Trash2, Volume2, X } from 'lucide-react';

import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';
import {
  CHAT_GREETING,
  CHAT_PLACEHOLDER,
  CHAT_STARTERS,
  CHAT_TITLE,
  CHAT_UI,
  SPEECH_LOCALE,
  TOOL_LABEL,
} from '@/lib/i18n/chatCopy';
import { chatApi, type ChatContext, type ChatLang, type ChatPersona, type ChatReply, type ChatSource, type ToolUse } from '@/services/chatApi';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isError?: boolean;
  meta?: { sources: ChatSource[]; tools: ToolUse[]; grounded: boolean; mode: ChatReply['mode'] };
}

const STORE = (persona: ChatPersona) => `mandisense-chat-v1-${persona}`;
const MAX_STORED = 40;
const LANG_CHIPS: Array<{ id: ChatLang; label: string }> = [
  { id: 'en', label: 'EN' },
  { id: 'kn', label: 'ಕನ್' },
  { id: 'hi', label: 'हि' },
];

const uid = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;

function load(persona: ChatPersona): Message[] {
  try {
    const raw = localStorage.getItem(STORE(persona));
    const parsed = raw ? (JSON.parse(raw) as Message[]) : [];
    return Array.isArray(parsed) ? parsed.filter((m) => m && typeof m.text === 'string').slice(-MAX_STORED) : [];
  } catch {
    return [];
  }
}

function save(persona: ChatPersona, messages: Message[]) {
  try {
    localStorage.setItem(STORE(persona), JSON.stringify(messages.filter((m) => !m.isError).slice(-MAX_STORED)));
  } catch {
    /* storage unavailable: the chat still works, it just is not remembered */
  }
}

/** Plain text with "•" or "- " lines as a list. Never injects HTML. */
function Rich({ text }: { text: string }) {
  const blocks: Array<{ list: boolean; lines: string[] }> = [];
  for (const line of text.split('\n')) {
    const bullet = /^\s*[•\-*]\s+/.test(line);
    const clean = bullet ? line.replace(/^\s*[•\-*]\s+/, '') : line;
    const last = blocks[blocks.length - 1];
    if (last && last.list === bullet) last.lines.push(clean);
    else blocks.push({ list: bullet, lines: [clean] });
  }
  return (
    <>
      {blocks.map((b, i) =>
        b.list ? (
          <ul key={i} className="my-1 list-disc space-y-1 pl-5">
            {b.lines.map((l, j) => (
              <li key={j}>{l}</li>
            ))}
          </ul>
        ) : (
          <React.Fragment key={i}>
            {b.lines.map((l, j) => (
              <p key={j} className={l ? 'mt-1.5 first:mt-0' : 'h-1'}>
                {l}
              </p>
            ))}
          </React.Fragment>
        ),
      )}
    </>
  );
}

export interface ChatPanelProps {
  persona: ChatPersona;
  variant: 'farm' | 'desk';
  lang: ChatLang;
  /** Present for the trader desk, which has no app-wide language switch. */
  onLangChange?: (l: ChatLang) => void;
  /** What the person is looking at: used as defaults when a question does not say. */
  context: ChatContext;
  onClose: () => void;
}

export default function ChatPanel({ persona, variant, lang, onLangChange, context, onClose }: ChatPanelProps) {
  const reduce = useReducedMotion();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastEntities, setLastEntities] = useState<Record<string, unknown>>({});
  const [failed, setFailed] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const [mounted, setMounted] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const farm = variant === 'farm';

  useEffect(() => {
    setMessages(load(persona));
    setMounted(true);
    inputRef.current?.focus();
    return () => abortRef.current?.abort();
  }, [persona]);

  useEffect(() => {
    if (mounted) save(persona, messages);
    endRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'end' });
  }, [messages, loading, mounted, persona, reduce]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const send = useCallback(
    async (raw: string) => {
      const q = raw.trim().slice(0, 1000);
      if (!q || loading) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const history = messages
        .filter((m) => !m.isError)
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.text }));
      setMessages((prev) => [...prev, { id: uid(), role: 'user', text: q }]);
      setInput('');
      setFailed(null);
      setLoading(true);
      setSlow(false);
      const slowTimer = setTimeout(() => setSlow(true), 8000);
      const hardTimer = setTimeout(() => ctrl.abort(), 120000);
      try {
        const r = await chatApi.send({ persona, message: q, lang, history, context: { ...context, last_entities: lastEntities } }, ctrl.signal);
        setLastEntities(r.context ?? {});
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: 'assistant', text: r.reply, meta: { sources: r.sources ?? [], tools: r.tools_used ?? [], grounded: r.grounded, mode: r.mode } },
        ]);
      } catch (err) {
        if ((err as Error)?.name === 'AbortError' && abortRef.current !== ctrl) return; // superseded or closed
        setFailed(q);
        setMessages((prev) => [...prev, { id: uid(), role: 'assistant', text: CHAT_UI.error[lang], isError: true }]);
      } finally {
        clearTimeout(slowTimer);
        clearTimeout(hardTimer);
        setSlow(false);
        setLoading(false);
      }
    },
    [context, lang, lastEntities, loading, messages, persona],
  );

  const { isListening, isRecognitionSupported, startListening, stopListening, speak, isSpeaking, isSynthesisSupported } = useVoiceAssistant({
    locale: SPEECH_LOCALE[lang],
    onResult: (said) => {
      setInput(said);
      send(said);
    },
  });

  const clear = () => {
    abortRef.current?.abort();
    setMessages([]);
    setLastEntities({});
    setFailed(null);
    setLoading(false);
  };

  const starters = useMemo(() => CHAT_STARTERS[persona].map((r) => r[lang]), [persona, lang]);
  const lastMode = [...messages].reverse().find((m) => m.meta)?.meta?.mode;
  const showStarters = messages.length === 0;

  return (
    <motion.section
      role="dialog"
      aria-label={CHAT_TITLE[persona][lang]}
      initial={reduce ? false : { opacity: 0, y: 24, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={reduce ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.97 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      className={`chat-panel ${farm ? 'chat-farm' : 'chat-desk'} fixed inset-x-2 bottom-2 top-[4.5rem] z-[70] flex flex-col overflow-hidden rounded-3xl md:inset-x-auto md:bottom-6 md:right-6 md:top-auto md:h-[min(42rem,calc(100dvh-3rem))] md:w-[26rem]`}
    >
      {/* header */}
      <header className="chat-head flex items-center gap-3 px-4 py-3.5">
        <span className="chat-avatar flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl">
          <Sparkles className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display truncate text-base font-extrabold leading-tight">{CHAT_TITLE[persona][lang]}</h2>
          <p className="flex items-center gap-1.5 truncate text-[11px] font-semibold opacity-80">
            <Globe2 className="h-3 w-3 shrink-0" />
            {lastMode === 'llm' ? CHAT_UI.modeLlm[lang] : CHAT_UI.modeTools[lang]}
          </p>
        </div>
        {onLangChange && (
          <div role="group" aria-label={CHAT_UI.language[lang]} className="flex shrink-0 overflow-hidden rounded-lg border border-white/25">
            {LANG_CHIPS.map((c) => (
              <button
                key={c.id}
                type="button"
                aria-pressed={lang === c.id}
                onClick={() => onLangChange(c.id)}
                className={`chat-lang px-2 py-1.5 text-[11px] font-bold ${lang === c.id ? 'chat-lang-on' : ''}`}
              >
                {c.label}
              </button>
            ))}
          </div>
        )}
        <button type="button" onClick={clear} aria-label={CHAT_UI.clear[lang]} title={CHAT_UI.clear[lang]} className="chat-icon-btn flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
          <Trash2 className="h-[18px] w-[18px]" />
        </button>
        <button type="button" onClick={onClose} aria-label={CHAT_UI.close[lang]} className="chat-icon-btn flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
          <X className="h-5 w-5" />
        </button>
      </header>

      {/* conversation */}
      <div className="chat-scroll min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite" aria-relevant="additions">
        <div className="chat-bot rounded-2xl rounded-tl-md px-3.5 py-3 text-[15px] leading-relaxed">
          <Rich text={CHAT_GREETING[persona][lang]} />
        </div>

        {showStarters && (
          <div className="flex flex-wrap gap-2 pt-1">
            {starters.map((s) => (
              <button key={s} type="button" onClick={() => send(s)} className="chat-chip rounded-full px-3.5 py-2 text-left text-[13.5px] font-semibold">
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m) => (
          <motion.div
            key={m.id}
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className={m.role === 'user' ? 'flex justify-end' : 'flex flex-col items-start'}
          >
            <div
              className={`max-w-[88%] rounded-2xl px-3.5 py-3 text-[15px] leading-relaxed ${
                m.role === 'user' ? 'chat-user rounded-tr-md' : m.isError ? 'chat-error rounded-tl-md' : 'chat-bot rounded-tl-md'
              }`}
            >
              <Rich text={m.text} />
            </div>

            {m.role === 'assistant' && !m.isError && m.meta && (
              <div className="mt-1.5 flex max-w-[92%] flex-col gap-1.5 pl-1">
                {m.meta.tools.length > 0 && (
                  <p className="chat-meta flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11.5px]">
                    <Check className="h-3 w-3" />
                    <span className="font-bold">{CHAT_UI.checked[lang]}:</span>
                    {[...new Set(m.meta.tools.map((t) => t.tool))].map((t) => (
                      <span key={t}>{TOOL_LABEL[t]?.[lang] ?? t}</span>
                    ))}
                  </p>
                )}
                {m.meta.sources.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="chat-meta text-[11.5px] font-bold">{CHAT_UI.sources[lang]}:</span>
                    {m.meta.sources.slice(0, 3).map((s) => (
                      <a
                        key={s.url}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="chat-source farm-focus inline-flex max-w-[11rem] items-center gap-1 rounded-full px-2.5 py-1 text-[11.5px] font-semibold"
                      >
                        <span className="truncate">{s.title.replace(/^https?:\/\//, '')}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ))}
                  </div>
                )}
                {!m.meta.grounded && (
                  <p className="flex items-start gap-1.5 text-[11.5px] font-semibold text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                    {CHAT_UI.unverified[lang]}
                  </p>
                )}
                {isSynthesisSupported && (
                  <button type="button" onClick={() => speak(m.text)} className="chat-meta farm-focus flex w-fit items-center gap-1.5 rounded-lg py-1 text-[12px] font-bold">
                    <Volume2 className={`h-3.5 w-3.5 ${isSpeaking ? 'animate-pulse' : ''}`} />
                    {CHAT_UI.readAloud[lang]}
                  </button>
                )}
              </div>
            )}

            {m.isError && failed && (
              <button type="button" onClick={() => send(failed)} className="chat-chip mt-2 flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[13px] font-bold">
                <RotateCcw className="h-3.5 w-3.5" /> {CHAT_UI.retry[lang]}
              </button>
            )}
          </motion.div>
        ))}

        {loading && (
          <div className="chat-bot flex w-fit items-center gap-3 rounded-2xl rounded-tl-md px-3.5 py-3 text-[14px]" role="status">
            <span className="flex gap-1" aria-hidden="true">
              {[0, 1, 2].map((i) => (
                <span key={i} className="chat-dot h-2 w-2 rounded-full" style={{ animationDelay: `${i * 0.16}s` }} />
              ))}
            </span>
            {slow ? CHAT_UI.waking[lang] : CHAT_UI.thinking[lang]}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="chat-composer flex items-center gap-2 px-3 pb-3 pt-2.5"
      >
        {isRecognitionSupported && (
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            aria-label={isListening ? CHAT_UI.listening[lang] : CHAT_UI.speak[lang]}
            aria-pressed={isListening}
            className={`chat-mic flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${isListening ? 'chat-mic-on' : ''}`}
          >
            <Mic className={`h-5 w-5 ${isListening ? 'animate-pulse' : ''}`} />
          </button>
        )}
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isListening ? CHAT_UI.listening[lang] : CHAT_PLACEHOLDER[persona][lang]}
          aria-label={CHAT_PLACEHOLDER[persona][lang]}
          maxLength={1000}
          lang={lang}
          className="chat-input h-12 min-w-0 flex-1 rounded-full px-4 text-[15px] outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label={CHAT_UI.send[lang]}
          className="chat-send flex h-12 w-12 shrink-0 items-center justify-center rounded-full disabled:opacity-45"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </button>
      </form>
      <p className="chat-meta px-4 pb-3 text-center text-[11px]">{CHAT_UI.disclaimer[lang]}</p>
    </motion.section>
  );
}

