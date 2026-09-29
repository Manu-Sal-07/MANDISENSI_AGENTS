'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Volume2 } from 'lucide-react';
import ProduceIcon, { resolveProduce, produceScript } from './ProduceIcon';
import { useLanguage } from '@/context/LanguageContext';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';

/**
 * The decision, at the size it deserves.
 *
 * This is the one loud thing on the farmer surface and everything else is
 * kept quiet around it. The reasoning: a farmer opens this to settle a
 * single question — sell today, or wait — and every pixel spent on
 * anything else is a pixel spent making that question harder to answer.
 *
 * Three things carry the answer before the words do: the colour band, the
 * verb, and the produce. Someone who reads slowly, or reads Devanagari
 * rather than Latin, still gets it at a glance from across a mandi yard.
 */

export type Call = 'SELL' | 'HOLD' | 'WAIT' | 'UNKNOWN';

/**
 * What the backend says produced this verb.
 *
 *   ADVISED      a directional call at a threshold whose precision was
 *                measured on held-out folds
 *   ABSTAINED    a forecast exists and the policy declined to call it
 *   UNAVAILABLE  there is no forecast for this series at all
 *
 * The first two are answers. The third is the absence of one, and it used
 * to render identically to the second -- both arrived as the string "WAIT"
 * and both were drawn as a confident amber tile with a 0.0% move beside it.
 */
export type CallType = 'ADVISED' | 'ABSTAINED' | 'UNAVAILABLE';

interface CallVisual {
  /** English verb, phrased as the action the farmer takes. */
  verb: string;
  /** Two-word form for chips and rows, where the long verb clipped to
      "Wait a f…" — and the verb is the one thing that must never clip. */
  verbShort: string;
  hindi: string;
  hindiShort: string;
  /** Kannada verb -- the first-read language for this app's actual
      audience (every tracked mandi is in Karnataka). */
  kannada: string;
  kannadaShort: string;
  /** What it means, in the plainest words available. */
  plain: string;
  colour: string;
  wash: string;
}

export const CALL_VISUAL: Record<Call, CallVisual> = {
  SELL: {
    verb: 'Sell now',
    verbShort: 'Sell now',
    hindi: 'अभी बेचें',
    hindiShort: 'अभी बेचें',
    kannada: 'ಈಗಲೇ ಮಾರಿ',
    kannadaShort: 'ಈಗಲೇ ಮಾರಿ',
    plain: 'Prices are falling. Today is better than next week.',
    colour: 'var(--call-sell)',
    wash: 'var(--call-sell-wash)',
  },
  HOLD: {
    verb: 'Hold',
    verbShort: 'Hold',
    hindi: 'रोकें',
    hindiShort: 'रोकें',
    kannada: 'ಇಡಿ',
    kannadaShort: 'ಇಡಿ',
    plain: 'Prices are climbing. Waiting should pay more.',
    colour: 'var(--call-hold)',
    wash: 'var(--call-hold-wash)',
  },
  WAIT: {
    verb: 'Wait a few days',
    verbShort: 'Wait',
    hindi: 'कुछ दिन रुकें',
    hindiShort: 'रुकें',
    kannada: 'ಕೆಲವು ದಿನ ಕಾಯಿರಿ',
    kannadaShort: 'ಕಾಯಿರಿ',
    plain: 'The market has not decided yet. Check again soon.',
    colour: 'var(--call-wait)',
    wash: 'var(--call-wait-wash)',
  },
  // Not a call. The wording says who is silent -- us, not the market --
  // because "wait" told a farmer the market was undecided when in fact we
  // had nothing to read at all, and those lead to different actions.
  UNKNOWN: {
    verb: 'No reading yet',
    verbShort: 'No reading',
    hindi: 'अभी जानकारी नहीं',
    hindiShort: 'जानकारी नहीं',
    kannada: 'ಇನ್ನೂ ಮಾಹಿತಿ ಇಲ್ಲ',
    kannadaShort: 'ಮಾಹಿತಿ ಇಲ್ಲ',
    plain: 'We do not have enough recent mandi records for this crop yet.',
    colour: 'var(--call-unknown)',
    wash: 'var(--call-unknown-wash)',
  },
};

export function normaliseCall(value?: string | null): Call {
  const upper = (value || '').toUpperCase();
  if (upper === 'SELL' || upper === 'HOLD' || upper === 'WAIT') return upper;
  // EXECUTE and BUY both mean "act now" to a seller.
  if (upper === 'BUY' || upper === 'EXECUTE') return 'SELL';
  // An unrecognised verb is not a quiet WAIT. WAIT is a real recommendation
  // -- "the market has not decided" -- and asserting it for a string we
  // failed to parse is the same fabrication this taxonomy exists to stop.
  return 'UNKNOWN';
}

/**
 * The verb to draw, given both what the backend decided and what produced
 * it. `callType` is authoritative: an UNAVAILABLE result carries the verb
 * "WAIT" for older clients, and rendering that verb is precisely the bug.
 */
export function resolveCall(input: {
  decision?: string | null;
  call_type?: string | null;
}): Call {
  if ((input.call_type || '').toUpperCase() === 'UNAVAILABLE') return 'UNKNOWN';
  return normaliseCall(input.decision);
}

interface CallCardProps {
  commodity: string;
  mandiName: string;
  call: Call;
  /** Expected move over the coming days, as a percentage. */
  changePct?: number | null;
  price?: number | null;
  /** Model's own words, shown under the verb when present. */
  note?: string | null;
  confidence?: number | null;
}

const formatRupees = (value?: number | null) =>
  value == null || Number.isNaN(value)
    ? null
    : `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;

/**
 * The cognition engine writes its reasoning for a log, not for a farmer.
 * A real example:
 *
 *   "In bangalore_yeshwanthpur, ginger prices are expected to downward by
 *    approximately 0.9%. Declining arrivals suggest tightening supply,
 *    which supports price levels."
 *
 * The first sentence is unusable here on three counts: it prints the raw
 * mandi slug, it is ungrammatical ("expected to downward"), and the number
 * it carries is already shown as "Expected move" right below. The second
 * sentence is the part worth reading — it says *why*.
 *
 * So sentences that are redundant or machine-broken are dropped and the
 * first well-formed one is kept. Nothing is rewritten and nothing is
 * invented; if none survives, the card falls back to its own plain line
 * rather than printing something the engine did not say.
 */
const MACHINE_PROSE = [
  /_/, // a raw slug such as bangalore_yeshwanthpur
  /expected to (downward|upward)/i, // missing verb
  /approximately\s*-?\d/i, // the figure already shown as "Expected move"
];

export function tidyNote(note: string | null | undefined, fallback: string): string {
  if (!note) return fallback;

  const sentences = note
    .split(/(?<=\.)\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  // The engine builds to its conclusion, so the *last* usable sentence is
  // the one that actually explains the verb. Taking the first gave tomato
  // "arrivals are increasing, which puts downward pressure on prices"
  // under a WAIT heading, when the engine's own closing line was "it is
  // safer to wait for clearer signals" — the sentence a farmer needs.
  const usable = [...sentences]
    .reverse()
    .find(
      (sentence) =>
        sentence.length >= 30 &&
        sentence.length <= 180 &&
        !MACHINE_PROSE.some((pattern) => pattern.test(sentence))
    );

  return usable ?? fallback;
}

export default function CallCard({
  commodity,
  mandiName,
  call,
  changePct,
  price,
  note,
  confidence,
}: CallCardProps) {
  const visual = CALL_VISUAL[call];
  const produce = resolveProduce(commodity);
  const rupees = formatRupees(price);
  const { lang, speechLocale, t } = useLanguage();
  const { speak, isSpeaking, isSynthesisSupported } = useVoiceAssistant({ locale: speechLocale });

  const spokenLine = tidyNote(note, visual.plain);
  const spokenScript = produceScript(produce, lang);
  const readAloud = () => {
    const verb = lang === 'kn' ? visual.kannada : lang === 'hi' ? visual.hindi : visual.verb;
    speak(`${spokenScript.text}. ${verb}. ${spokenLine}`);
  };
  // An UNKNOWN call means nothing was measured, but callers routinely still
  // pass a placeholder `changePct: 0.0` / `confidence: 0.0` alongside it
  // (the backend's own refusal shape sets both to zero rather than
  // omitting them). Rendering those numbers under "No reading yet" told a
  // farmer the market was flat and we were unsure -- two measurements we
  // never made -- so they are suppressed here rather than at every call
  // site individually.
  const showNumbers = call !== 'UNKNOWN';

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
      className="farm-card farm-card-lift relative overflow-hidden"
    >
      {/* The colour band is the first thing read, and the only place the
          decision colour is used at full strength. */}
      <div className="h-2.5 w-full" style={{ background: visual.colour }} />

      <div className="p-6 sm:p-8">
        {/* Produce stays beside the verb rather than stacking above it:
            stacking left it orphaned on its own line and pushed the answer
            below the fold on a small phone. It shrinks instead. */}
        <div className="flex items-start gap-4 sm:gap-5">
          <span className="shrink-0 sm:hidden">
            <ProduceIcon name={commodity} size="lg" plated={false} sway />
          </span>
          <span className="hidden shrink-0 sm:block">
            <ProduceIcon name={commodity} size="xl" plated={false} sway />
          </span>

          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-[var(--farm-ink-soft)]">
              {produce.label} · {mandiName}
            </p>

            <h2
              className="farm-display mt-1 text-4xl leading-[1.05] sm:text-5xl"
              style={{ color: visual.colour }}
            >
              {visual.verb}
            </h2>
            <p
              className="farm-display text-2xl leading-tight sm:text-3xl"
              style={{ color: visual.colour, opacity: 0.75 }}
              lang={lang === 'kn' ? 'kn' : 'hi'}
            >
              {lang === 'kn' ? visual.kannada : visual.hindi}
            </p>

            <p className="mt-3 max-w-[46ch] text-base leading-relaxed text-[var(--farm-ink)]">
              {spokenLine}
            </p>

            {isSynthesisSupported && (
              <button
                type="button"
                onClick={readAloud}
                aria-label={t('voice.read_aloud')}
                className="farm-focus mt-2.5 flex items-center gap-1.5 rounded-full border border-[var(--farm-line)] bg-white/70 px-3 py-1.5 text-xs font-bold text-[var(--farm-ink-soft)] transition-colors hover:border-[var(--leaf)] hover:text-[var(--leaf)]"
              >
                <Volume2 className={`h-3.5 w-3.5 ${isSpeaking ? 'animate-pulse' : ''}`} />
                {t('voice.read_aloud')}
              </button>
            )}
          </div>
        </div>

        {/* Supporting numbers, kept quiet. They justify the verb; they are
            not the answer, so they do not compete with it. Suppressed
            entirely for an UNKNOWN call — see `showNumbers` above. */}
        {showNumbers && (rupees || changePct != null || confidence != null) && (
          <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-4 border-t border-[var(--farm-line)] pt-5">
            {rupees && (
              <div>
                <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                  Price today
                </dt>
                <dd className="farm-display text-2xl text-[var(--farm-ink)]">{rupees}</dd>
              </div>
            )}
            {changePct != null && (
              <div>
                <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                  Expected move
                </dt>
                <dd className="farm-display text-2xl" style={{ color: visual.colour }}>
                  {changePct > 0 ? '+' : ''}
                  {changePct.toFixed(1)}%
                </dd>
              </div>
            )}
            {confidence != null && (
              <div>
                <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                  How sure
                </dt>
                <dd className="flex items-center gap-2 pt-1.5">
                  {/* Confidence as filled bars rather than a percentage:
                      "3 of 4" is legible without numeracy. */}
                  {[0, 1, 2, 3].map((i) => (
                    <span
                      key={i}
                      className="block h-2.5 w-6 rounded-full"
                      style={{
                        background:
                          i < Math.round((confidence || 0) * 4)
                            ? visual.colour
                            : 'var(--farm-line)',
                      }}
                    />
                  ))}
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
    </motion.div>
  );
}
