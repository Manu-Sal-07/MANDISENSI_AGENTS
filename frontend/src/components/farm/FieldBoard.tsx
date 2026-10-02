'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Store, Wheat, History, ArrowLeftRight, CalendarClock, PackageOpen, Sparkles, Timer, TrendingDown, TrendingUp, Volume2, type LucideIcon } from 'lucide-react';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';
import { placeName, reasonText, rupees, say, shortDate } from '@/lib/i18n/farmCopy';
import { farmerApi, type FarmBoard, type FarmReason } from '@/services/farmerApi';
import MandiBoard from './MandiBoard';
import ProduceIcon, { produceScript, resolveProduce } from './ProduceIcon';
import SupplyMeter from './SupplyMeter';
import CountUp from './charts/CountUp';
import PricePath from './charts/PricePath';
import { toneOf } from './callTone';

const REASON_ICON: Record<FarmReason['code'], LucideIcon> = {
  price_up_week: TrendingUp,
  price_down_week: TrendingDown,
  arrivals_high: PackageOpen,
  arrivals_low: PackageOpen,
  above_last_year: CalendarClock,
  below_last_year: CalendarClock,
  model_expects_up: Sparkles,
  model_expects_down: Sparkles,
  spoils_fast: Timer,
  neighbours_dearer: ArrowLeftRight,
  neighbours_cheaper: ArrowLeftRight,
};

function callSentence(board: FarmBoard, cropLabel: string, lang: 'en' | 'hi' | 'kn'): string {
  const c = board.call;
  if (c.type === 'ADVISED') return say(c.decision === 'SELL' ? 'call.sell.why' : 'call.hold.why', lang, { n: c.horizon });
  if (c.type === 'ABSTAINED') return say('call.wait.why', lang, { n: c.horizon });
  if (c.type === 'RANGE_ONLY') return say('call.range.why', lang, { crop: cropLabel });
  return say('call.none.why', lang);
}

/** The top of the app: one crop, one district, what it is worth and what to do. */
export default function FieldBoard() {
  const { district, crop } = useFarm();
  const { lang, speechLocale } = useLanguage();
  const { speak, isSpeaking, isSynthesisSupported } = useVoiceAssistant({ locale: speechLocale });

  const { data: board, isLoading, isError } = useQuery({
    queryKey: ['farm-board', district, crop],
    queryFn: () => farmerApi.board(district, crop),
  });

  const produce = resolveProduce(crop);
  const cropLabel = produceScript(produce, lang).text;

  if (isLoading) return <div className="farm-card h-[34rem] animate-pulse bg-white/70" />;
  if (isError || !board || board.status !== 'OK') {
    return (
      <div className="farm-card p-6">
        <p className="text-base font-semibold text-[var(--farm-ink)]">{say('mandis.empty', lang)}</p>
      </div>
    );
  }

  const tone = toneOf(board.call, lang);
  const week = board.changes.d7;
  const sentence = callSentence(board, cropLabel, lang);
  const readAloud = () =>
    speak(`${cropLabel}. ${rupees(board.price.value)} ${say('unit.qtl', lang)}. ${tone.key === 'range' ? '' : tone.label + '.'} ${sentence}`);

  return (
    <motion.section
      key={`${district}-${crop}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="farm-card relative overflow-hidden"
    >
      <div className="h-2" style={{ background: tone.colour }} />
      <div className="pointer-events-none absolute inset-x-0 top-2 h-44" style={{ background: `linear-gradient(180deg, ${tone.wash} 0%, transparent 100%)`, opacity: 0.9 }} aria-hidden="true" />

      <div className="p-5 sm:p-7">
        <div className="flex items-start gap-4">
          <ProduceIcon name={crop} size="lg" plated={false} sway />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-[var(--farm-ink-soft)]">
              {cropLabel} · {placeName(board.district_name, lang)}
            </p>
            <p className="farm-display text-[3.25rem] leading-none text-[var(--farm-ink)] sm:text-[4rem]">
              <CountUp value={board.price.value} />
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--farm-ink-soft)]">
              <span>{say('unit.qtl', lang)}</span>
              {week != null && (
                <span className="flex items-center gap-1 font-bold tabular-nums" style={{ color: week >= 0 ? 'var(--leaf-deep)' : 'var(--call-sell)' }}>
                  {week >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  {Math.abs(week).toFixed(1)}% {say('change.week', lang)}
                </span>
              )}
            </p>
          </div>
        </div>

        {/* The call, only as loud as the record behind it. */}
        <div className="mt-5 rounded-2xl p-4" style={{ background: tone.wash }}>
          <div className="flex items-center justify-between gap-3">
            <p className="farm-display text-2xl leading-tight" style={{ color: tone.colour }}>{tone.label}</p>
            {isSynthesisSupported && (
              <button
                type="button"
                onClick={readAloud}
                className="farm-focus flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--farm-line-strong)] bg-white/80 px-3 py-1.5 text-xs font-bold text-[var(--farm-ink-soft)] hover:border-[var(--leaf)] hover:text-[var(--leaf)]"
              >
                <Volume2 className={`h-3.5 w-3.5 ${isSpeaking ? 'animate-pulse' : ''}`} />
                {lang === 'kn' ? 'ಗಟ್ಟಿಯಾಗಿ ಓದಿ' : lang === 'hi' ? 'ज़ोर से पढ़ें' : 'Read aloud'}
              </button>
            )}
          </div>
          <p className="mt-1.5 max-w-[52ch] text-[15px] leading-relaxed text-[var(--farm-ink)]">{sentence}</p>
        </div>

        <div className="mt-6">
          <PricePath board={board} />
        </div>

        {board.reasons.length > 0 && (
          <ul className="mt-5 grid gap-2.5 sm:grid-cols-2">
            {board.reasons.map((r) => {
              const Icon = REASON_ICON[r.code];
              return (
                <li key={r.code} className="flex items-start gap-3 rounded-xl bg-[var(--farm-paper-warm)] px-3.5 py-3">
                  <Icon className="mt-0.5 h-[18px] w-[18px] shrink-0 text-[var(--farm-ink-soft)]" />
                  <span className="text-sm leading-snug text-[var(--farm-ink)]">{reasonText(r, lang)}</span>
                </li>
              );
            })}
          </ul>
        )}

        <p className="mt-4 text-xs text-[var(--farm-ink-faint)]">{say('asof', lang, { d: shortDate(board.price.date, lang) })}</p>
      </div>
    </motion.section>
  );
}

export function BoardSide() {
  const { district, crop } = useFarm();
  const { lang } = useLanguage();
  const { data: board } = useQuery({
    queryKey: ['farm-board', district, crop],
    queryFn: () => farmerApi.board(district, crop),
  });
  if (!board || board.status !== 'OK') return null;
  const last = board.seasonal?.last_year;

  return (
    <div className="space-y-6">
      <section className="farm-section">
        <div className="farm-h2">
          <span className="farm-section-icon bg-[var(--leaf-wash)] text-[var(--leaf-deep)]"><Store className="h-5 w-5" /></span>
          <div>
            <h2 className="farm-display text-xl leading-tight text-[var(--farm-ink)]">{say('mandis.title', lang)}</h2>
            <p className="text-sm text-[var(--farm-ink-faint)]">{say('mandis.sub', lang)}</p>
          </div>
        </div>
        <div className="mb-3" />
        <MandiBoard mandis={board.mandis} />
      </section>

      {board.supply && (
        <section className="farm-section">
          <div className="farm-h2 mb-1">
            <span className="farm-section-icon bg-[var(--turmeric-wash)] text-[#b8801a]"><Wheat className="h-5 w-5" /></span>
            <h2 className="farm-display text-xl text-[var(--farm-ink)]">{say('supply.title', lang)}</h2>
          </div>
          <SupplyMeter supply={board.supply} />
        </section>
      )}

      {last && (
        <section className="farm-section farm-section-warm">
          <div className="farm-h2">
            <span className="farm-section-icon bg-white/80 text-[var(--soil)]"><History className="h-5 w-5" /></span>
            <h2 className="farm-display text-xl text-[var(--farm-ink)]">{say('year.title', lang)}</h2>
          </div>
          <p className="mt-2 text-[15px] text-[var(--farm-ink)]">{say('year.body', lang, { p: new Intl.NumberFormat('en-IN').format(Math.round(last.price)) })}</p>
          {last.change_pct != null && (
            <p className="farm-display mt-1 text-2xl tabular-nums" style={{ color: last.change_pct >= 0 ? 'var(--leaf-deep)' : 'var(--call-sell)' }}>
              {last.change_pct >= 0 ? '+' : '−'}{Math.abs(last.change_pct).toFixed(0)}%
            </p>
          )}
        </section>
      )}
    </div>
  );
}
