'use client';

/**
 * Farmer home.
 *
 * The page answers one question — sell today or wait — for whoever is
 * holding the phone at a mandi gate. Everything is arranged around that:
 * the decision is the hero rather than the brand, the produce is drawn
 * rather than coded, and the surface stays bright because it is read
 * outdoors in direct sun.
 *
 * The trader views (terminal, market explorer, intelligence lab) keep the
 * dark data-dense system; the divergence is scoped to `.farm-surface`.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Clock, MapPin, Wallet, X, type LucideIcon } from 'lucide-react';

import FarmScene from '@/components/farm/FarmScene';
import CallCard, { resolveCall } from '@/components/farm/CallCard';
import TodaysCalls from '@/components/farm/TodaysCalls';
import AskBar from '@/components/farm/AskBar';
import NearbyMandis from '@/components/farm/NearbyMandis';
import { mandiApi } from '@/services/api';
import { QueryResponse } from '@/types/mandi';
import { useLanguage } from '@/context/LanguageContext';

const EASE = [0.16, 1, 0.3, 1] as const;

export default function FarmerHome() {
  const [isAsking, setIsAsking] = useState(false);
  const [answer, setAnswer] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();

  // The headline call is whatever the market is shouting loudest about
  // today. It fills the hero before the farmer has typed anything, so the
  // page is useful on arrival rather than only after a search.
  const { data: feed } = useQuery({
    queryKey: ['discovery-feed', 'bengaluru'],
    queryFn: () => mandiApi.getDiscoveryFeed('bengaluru'),
    staleTime: 1000 * 60 * 5,
  });

  const headline = Array.isArray(feed) && feed.length ? feed[0] : null;

  const handleAsk = async (question: string) => {
    setIsAsking(true);
    setAnswer(null);
    setError(null);
    try {
      setAnswer(await mandiApi.predictQuery(question));
    } catch {
      setError('Could not reach the market right now. Try again in a moment.');
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="farm-surface relative min-h-screen pb-28 md:pb-16">
      {/* ── The field ─────────────────────────────────────────── */}
      <section className="relative isolate overflow-hidden px-4 pb-8 pt-10 sm:pt-14">
        <FarmScene />

        <div className="relative mx-auto max-w-2xl lg:max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="text-center"
          >
            <p
              className="farm-display text-[2rem] leading-tight text-[var(--farm-ink)] sm:text-4xl"
              lang={lang}
            >
              {t('home.headline')}
            </p>
            {lang !== 'en' && (
              <p className="mt-1 text-lg font-semibold text-[var(--farm-ink-soft)] sm:text-xl">
                Sell today, or wait?
              </p>
            )}
          </motion.div>

          {/* On a phone this is one column: answer, then ask, stacked —
              there is no width to spare. From `lg` up, the ask bar moves
              beside the decision as a companion panel instead of sitting
              in the empty space beneath it. */}
          <div className="mt-7 lg:mt-10 lg:grid lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-start lg:gap-8">
            {/* ── The answer ──────────────────────────────────────── */}
            <div>
              <AnimatePresence mode="wait">
                {answer ? (
                  <motion.div
                    key="answer"
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.4, ease: EASE }}
                    className="relative"
                  >
                    <CallCard
                      commodity={answer.metadata?.commodity || 'produce'}
                      mandiName={prettyMandi(answer.metadata?.mandi_id)}
                      call={resolveCall({ decision: answer.decision, call_type: answer.call_type })}
                      note={answer.summary}
                      confidence={answer.metadata?.confidence ?? null}
                    />
                    <button
                      onClick={() => setAnswer(null)}
                      aria-label="Clear this answer"
                      className="farm-focus absolute right-4 top-6 flex h-10 w-10 items-center justify-center rounded-full bg-white/80 text-[var(--farm-ink-soft)] backdrop-blur transition-colors hover:text-[var(--farm-ink)]"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </motion.div>
                ) : headline ? (
                  <motion.div key="headline">
                    <CallCard
                      commodity={headline.hot_commodity}
                      mandiName={headline.mandi_name}
                      call={resolveCall(headline)}
                      changePct={headline.price_change_pct}
                      confidence={headline.confidence}
                      note={headline.reasoning}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="waiting"
                    className="farm-card farm-card-lift h-56 animate-pulse bg-white/70"
                  />
                )}
              </AnimatePresence>
            </div>

            {/* ── Ask ─────────────────────────────────────────────── */}
            <div className="farm-ask-panel mt-6 lg:mt-0">
              <p className="farm-display mb-4 hidden text-sm text-[var(--farm-ink-faint)] lg:block">
                {t('home.ask_another')}
              </p>
              <AskBar onAsk={handleAsk} isLoading={isAsking} />
              <AnimatePresence>
                {error && (
                  <motion.p
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    role="status"
                    className="mt-3 text-center text-sm font-semibold text-[var(--call-sell)]"
                  >
                    {error}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* ── Sell Plan CTA ───────────────────────────────────────
              The single most valuable answer this app can give -- where,
              when, and for how much -- lives one tap away from the hero
              rather than buried in the tools grid, because it is the
              feature the rest of the plan is built around. */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15, ease: EASE }}
            className="mt-6"
          >
            <Link
              href="/sell-plan"
              className="farm-focus flex items-center justify-center gap-3 rounded-2xl bg-[var(--leaf)] px-6 py-4 text-center shadow-[0_16px_36px_-18px_rgba(42,33,25,0.45)] transition-transform active:scale-[0.99]"
            >
              <Wallet className="h-5 w-5 shrink-0 text-white" />
              <span className="farm-display text-lg text-white sm:text-xl">
                {t('home.sell_plan_cta')}
              </span>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── Today's calls + Mandis near you ─────────────────────── *
          Two independent lists, so on a wide window they sit side by
          side instead of one narrow column stacked above the other with
          the rest of the screen empty. On a phone `lg:grid-cols-2` never
          applies, so this is still a plain vertical stack. */}
      <section className="mx-auto mt-6 grid w-full max-w-3xl gap-6 px-4 lg:max-w-5xl lg:grid-cols-2 lg:items-start">
        <div className="farm-section farm-section-warm">
          <SectionHeading icon={Clock} tint="turmeric" title={t('home.todays_calls')} lang={lang} />
          <TodaysCalls />
        </div>

        <div className="farm-section">
          <SectionHeading icon={MapPin} tint="leaf" title={t('home.mandis_near_you')} lang={lang} />
          <NearbyMandis />
        </div>
      </section>

      <footer className="mx-auto mt-14 max-w-3xl px-4 pb-4 text-center">
        <p className="text-sm text-[var(--farm-ink-faint)]">{t('home.footer_disclaimer')}</p>
      </footer>
    </div>
  );
}

/**
 * A section header carries an icon badge rather than plain text alone.
 * It borrows the same tinted-circle language FarmHeader already uses for
 * the location pin, so "today's calls" (turmeric — time-sensitive) and
 * "mandis near you" (leaf — place) read as two rooms of one house
 * instead of two unrelated headings.
 */
function SectionHeading({
  icon: Icon,
  tint,
  title,
  lang,
}: {
  icon: LucideIcon;
  tint: 'leaf' | 'turmeric';
  title: string;
  lang: string;
}) {
  const wash = tint === 'leaf' ? 'var(--leaf-wash)' : 'var(--turmeric-wash)';
  const fg = tint === 'leaf' ? 'var(--leaf)' : 'var(--call-wait)';
  return (
    <div className="farm-section-header">
      <span className="farm-section-icon" style={{ background: wash }}>
        <Icon className="h-5 w-5" style={{ color: fg }} />
      </span>
      <div className="min-w-0">
        <h2
          className="farm-display text-xl leading-tight text-[var(--farm-ink)] sm:text-2xl"
          lang={lang}
        >
          {title}
        </h2>
      </div>
    </div>
  );
}

function prettyMandi(id?: string | null): string {
  if (!id) return 'your mandi';
  return id
    .replace(/_apmc$/, '')
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
