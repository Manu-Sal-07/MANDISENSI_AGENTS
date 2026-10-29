'use client';

/**
 * How we know the sell advice works: the study behind it, including what failed.
 *
 * Every number is read from `/v1/market-choice/evidence`, which serves the
 * out-of-sample results of the GFMC study (five nested walk-forward test
 * blocks, 963 decision days). The page states the negative results and the
 * limits as plainly as the gains.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { BadgeCheck, FlaskConical, ShieldCheck, TriangleAlert, XCircle } from 'lucide-react';

import PageHero from '@/components/farm/PageHero';
import { useLanguage } from '@/context/LanguageContext';
import { tri } from '@/lib/i18n/farmCopy';
import { formatRupees } from '@/lib/format';
import { marketChoiceApi } from '@/services/marketChoiceApi';

const CLASS_COLOUR = { realised: '#0b6e4f', observed: '#8c8c8c', heuristic: '#c49a00' } as const;
const CLASS_LABEL = { realised: 'Learned from what farmers actually received', observed: 'Learned from observed prices only', heuristic: 'Simple rule' } as const;
const VERDICT = {
  better: { label: 'Helps', colour: '#0b6e4f' },
  worse: { label: 'Hurts', colour: '#b42318' },
  no_effect: { label: 'No measurable effect', colour: '#6b7280' },
} as const;

const card = 'rounded-3xl border border-[var(--farm-line)] bg-[var(--farm-paper)] p-5 sm:p-6';

export default function EvidencePage() {
  const { lang } = useLanguage();
  const { data, isLoading } = useQuery({ queryKey: ['mc-evidence'], queryFn: () => marketChoiceApi.evidence(), staleTime: 60 * 60 * 1000 });

  if (isLoading) return <div className="farm-surface min-h-screen" />;
  if (!data || data.status !== 'OK' || !data.decision) {
    return (
      <div className="farm-surface min-h-screen px-4 pt-10">
        <p className="mx-auto max-w-xl text-[var(--farm-ink-soft)]">{data?.reason ?? 'The evidence has not been exported yet.'}</p>
      </div>
    );
  }

  const methods = data.decision.methods;
  const best = methods.find((m) => m.method === 'lgbm_filled') ?? methods.find((m) => m.class === 'realised')!;
  const obs = methods.find((m) => m.method === 'lgbm_obs');
  const heur = methods.find((m) => m.method === 'highest_yesterday');
  const near = methods.find((m) => m.method === 'nearest_today');
  const maxRev = Math.max(...methods.map((m) => m.revenue), data.study?.oracle_revenue ?? 0);
  const floorTen = (data.floors ?? []).find((f) => f.predictor === 'SPO+ model' && f.policy === 'adaptive conformal floor' && f.alpha === 0.1);
  const naiveObs = (data.floors ?? []).find((f) => f.predictor === 'LightGBM, observed prices' && f.policy.startsWith('naive'));
  const gain = best && obs ? best.revenue - obs.revenue : 0;

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-3xl px-4 pb-10 pt-7 lg:max-w-4xl">
        <PageHero
          photo="mandi-yard"
          title={tri(lang, 'How we know this works', 'ಇದು ಕೆಲಸ ಮಾಡುತ್ತದೆ ಎಂದು ಹೇಗೆ ಗೊತ್ತು', 'हमें कैसे पता कि यह काम करता है')}
          subtitle={tri(lang, 'The test behind the advice, including what did not work.', 'ಸಲಹೆಯ ಹಿಂದಿನ ಪರೀಕ್ಷೆ, ಕೆಲಸ ಮಾಡದ್ದನ್ನೂ ಸೇರಿ.', 'सलाह के पीछे की जांच, जो काम नहीं आया वह भी।')}
          icon={<FlaskConical className="h-7 w-7" />}
        />

        <p className="mt-3 max-w-[64ch] text-[15px] leading-relaxed text-[var(--farm-ink-soft)]">
          We replayed {data.study?.decision_days} days of real mandi prices (Karnataka, 2024 to {data.study?.period?.[1]}). On each day a model that had only seen the
          past advised a farmer where and when to sell; we then compared it with what the farmer would really have received. No price is made up or filled in.
        </p>

        {/* the three things to remember */}
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            { icon: <BadgeCheck className="h-5 w-5" />, n: `+${formatRupees(gain)}`, t: 'more per quintal for a model trained on what farmers actually received than for the same model trained only on observed prices (tomato). The gain showed up in every test period.', c: '#0b6e4f' },
            { icon: <ShieldCheck className="h-5 w-5" />, n: floorTen ? `${(floorTen.violation * 100).toFixed(0)}%` : '—', t: `of the time the promised minimum was missed, against a 10% target. A simple rule for a minimum missed it ${naiveObs ? (naiveObs.violation * 100).toFixed(0) : '—'}% of the time.`, c: '#2f6fed' },
            { icon: <TriangleAlert className="h-5 w-5" />, n: near && heur ? formatRupees(heur.revenue - near.revenue) : '—', t: 'is what simply going to yesterday’s highest-priced mandi already earns over the nearest one. The advice has to beat that; each crop’s own track record (Floor Monitor) says whether it does.', c: '#c49a00' },
          ].map((c, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }} className={card}>
              <span style={{ color: c.c }}>{c.icon}</span>
              <p className="mt-2 font-mono text-3xl font-black" style={{ color: c.c }}>{c.n}</p>
              <p className="mt-1 text-sm leading-relaxed text-[var(--farm-ink-soft)]">{c.t}</p>
            </motion.div>
          ))}
        </div>

        {/* revenue chart */}
        <section className={`${card} mt-6`}>
          <h2 className="text-lg font-black text-[var(--farm-ink)]">What each approach earns (tomato, ₹ per quintal after costs)</h2>
          <div className="mt-4 space-y-1.5">
            {methods.map((m) => (
              <div key={m.method} className="flex items-center gap-2 text-xs">
                <span className="w-44 shrink-0 text-[var(--farm-ink-soft)] sm:w-60">{m.label}</span>
                <div className="h-4 flex-1 rounded-full bg-black/5">
                  <div className="h-4 rounded-full" style={{ width: `${(100 * m.revenue) / maxRev}%`, background: CLASS_COLOUR[m.class] }} />
                </div>
                <span className="w-14 text-right font-mono font-bold text-[var(--farm-ink)]">{formatRupees(m.revenue)}</span>
              </div>
            ))}
            <div className="flex items-center gap-2 text-xs">
              <span className="w-44 shrink-0 font-bold text-[var(--farm-ink)] sm:w-60">Best possible, in hindsight</span>
              <div className="h-4 flex-1 rounded-full bg-black/5"><div className="h-4 rounded-full" style={{ width: '100%', background: '#111827' }} /></div>
              <span className="w-14 text-right font-mono font-bold text-[var(--farm-ink)]">{formatRupees(data.study?.oracle_revenue)}</span>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--farm-ink-faint)]">
            {(Object.keys(CLASS_COLOUR) as Array<keyof typeof CLASS_COLOUR>).map((k) => (
              <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: CLASS_COLOUR[k] }} />{CLASS_LABEL[k]}</span>
            ))}
          </div>
        </section>

        {/* what produced the gain */}
        <section className={`${card} mt-6`}>
          <h2 className="text-lg font-black text-[var(--farm-ink)]">What made the difference, and what did not</h2>
          <p className="mt-1 text-sm text-[var(--farm-ink-soft)]">Each row compares two versions of the system. A difference counts only if it is clearly bigger than chance.</p>
          <ul className="mt-4 divide-y divide-[var(--farm-line)]">
            {(data.effects ?? []).slice(0, 14).map((e) => (
              <li key={e.label} className="flex items-center justify-between gap-3 py-2.5">
                <span className="text-sm text-[var(--farm-ink)]">{e.label.replace(/^\[[^\]]*\]\s*/, '')}</span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="font-mono text-xs text-[var(--farm-ink-faint)]">{e.diff > 0 ? '+' : ''}{e.diff.toFixed(0)} ₹/q</span>
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white" style={{ background: VERDICT[e.verdict].colour }}>{VERDICT[e.verdict].label}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-[var(--farm-ink-faint)]">Negative ₹/q means lower regret, i.e. a better result for the first system listed.</p>
        </section>

        {/* other crops */}
        <section className={`${card} mt-6`}>
          <h2 className="text-lg font-black text-[var(--farm-ink)]">Does it hold for other crops?</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[480px] text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--farm-ink-faint)]">
                  <th className="py-1.5 font-bold">Crop</th><th className="py-1.5 text-right font-bold">Mandis</th>
                  <th className="py-1.5 text-right font-bold">Observed prices</th><th className="py-1.5 text-right font-bold">Actual outcomes</th>
                  <th className="py-1.5 text-right font-bold">Gain (95% range)</th>
                </tr>
              </thead>
              <tbody>
                {(data.crops ?? []).map((c) => (
                  <tr key={c.crop} className="border-t border-[var(--farm-line)]">
                    <td className="py-2 font-bold capitalize text-[var(--farm-ink)]">{c.crop}</td>
                    <td className="py-2 text-right text-[var(--farm-ink-soft)]">{c.markets}</td>
                    <td className="py-2 text-right font-mono text-[var(--farm-ink-soft)]">{formatRupees(c.observed_labels)}</td>
                    <td className="py-2 text-right font-mono font-bold text-[var(--farm-ink)]">{formatRupees(c.realised_labels)}</td>
                    <td className="py-2 text-right font-mono text-[var(--farm-ink-soft)]">{formatRupees(-c.label_effect.diff)} ({formatRupees(-c.label_effect.ci_hi)} to {formatRupees(-c.label_effect.ci_lo)})</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* did not work + limits */}
        <section className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className={card}>
            <h2 className="flex items-center gap-2 text-lg font-black text-[var(--farm-ink)]"><XCircle className="h-5 w-5 text-[#b42318]" /> What did not work</h2>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[var(--farm-ink-soft)]">
              {(data.negative_results ?? []).map((n) => <li key={n.id}>• {n.text}</li>)}
            </ul>
          </div>
          <div className={card}>
            <h2 className="flex items-center gap-2 text-lg font-black text-[var(--farm-ink)]"><TriangleAlert className="h-5 w-5 text-[#c49a00]" /> Limits to keep in mind</h2>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[var(--farm-ink-soft)]">
              {(data.limitations ?? []).map((l) => <li key={l}>• {l}</li>)}
            </ul>
          </div>
        </section>

        {/* figures */}
        <section className="mt-6 space-y-5">
          <h2 className="text-lg font-black text-[var(--farm-ink)]">The figures from the study</h2>
          {(data.figures ?? []).map((f) => (
            <figure key={f.id} className={card}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={f.path} alt={f.title} className="w-full rounded-xl bg-white" loading="lazy" />
              <figcaption className="mt-3 text-sm leading-relaxed text-[var(--farm-ink-soft)]"><b className="text-[var(--farm-ink)]">{f.title}.</b> {f.caption}</figcaption>
            </figure>
          ))}
        </section>
        <p className="mt-6 text-xs text-[var(--farm-ink-faint)]">{data.source}. Generated {data.generated_at?.slice(0, 10)}.</p>
      </main>
    </div>
  );
}
