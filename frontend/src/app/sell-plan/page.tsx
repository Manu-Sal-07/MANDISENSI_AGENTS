'use client';

/**
 * Plan my sale.
 *
 * One load, one answer. Every rupee figure is on the same footing: what the
 * farmer's own mandi printed, less what travelling or waiting costs. A mandi
 * too small to take the load, or whose price is out of line with its
 * neighbours, is never recommended (see `farmer/transport.py`); waiting is
 * offered only for a crop whose record earned a call, and is shown with the
 * spoilage already taken off.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Check, Loader2, Minus, PiggyBank, Plus, Truck, Hourglass, Store } from 'lucide-react';

import ProduceIcon, { produceScript, resolveProduce } from '@/components/farm/ProduceIcon';
import UnavailableNotice from '@/components/farm/tools/UnavailableNotice';
import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { placeName, rupees, say, shortDate, tri } from '@/lib/i18n/farmCopy';
import { savePlan } from '@/lib/myMoney';
import { farmerApi, type CropId, type SellPlanOption } from '@/services/farmerApi';

const ICON = { sell_today: Store, travel: Truck, wait: Hourglass } as const;

const optionPlace = (o: SellPlanOption, lang: 'en' | 'hi' | 'kn') =>
  lang === 'kn' ? o.mandi_name_kn : lang === 'hi' ? o.mandi_name_hi : o.mandi_name;

export default function SellPlanPage() {
  const { districtInfo, crop, setCrop, mandi, setMandi, quantity, setQuantity } = useFarm();
  const { lang, t } = useLanguage();
  const [saved, setSaved] = useState(false);

  const mandis = districtInfo?.mandis ?? [];
  const activeMandi = mandi && mandis.some((m) => m.id === mandi) ? mandi : mandis[0]?.id ?? null;
  useEffect(() => setSaved(false), [crop, activeMandi, quantity]);

  const { data: plan, isFetching } = useQuery({
    queryKey: ['farm-sellplan', crop, activeMandi, quantity],
    queryFn: () => farmerApi.sellPlan(crop, activeMandi as string, quantity),
    enabled: !!activeMandi && quantity > 0,
  });

  const options = useMemo(() => (plan?.status === 'OK' ? plan.options ?? [] : []), [plan]);
  const top = useMemo(() => Math.max(1, ...options.map((o) => o.total)), [options]);
  const best = options.find((o) => o.choice === plan?.best);

  const label = (o: SellPlanOption) =>
    o.choice === 'sell_today' ? t('sellplan.option_sell_today') : o.choice === 'travel' ? t('sellplan.option_travel') : t('sellplan.option_wait');

  const follow = () => {
    if (!plan || !best || !activeMandi) return;
    const here = options[0];
    savePlan({
      commodity: crop,
      mandiId: activeMandi,
      mandiName: placeName(mandis.find((m) => m.id === activeMandi) ?? null, 'en') || here.mandi_name,
      quantityQuintals: quantity,
      choice: best.choice,
      planTotal: best.total,
      baselineTotal: plan.baseline_total ?? here.total,
      targetDate: best.target_date ?? new Date().toISOString().slice(0, 10),
      targetMandiId: best.mandi_id,
      targetMandiName: best.mandi_name,
    });
    setSaved(true);
  };

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-2xl px-4 pb-10 pt-7 lg:max-w-3xl">
        <h1 className="farm-display text-3xl text-[var(--farm-ink)]">{t('sellplan.title')}</h1>
        <p className="mt-1 text-sm text-[var(--farm-ink-faint)]">{t('sellplan.subtitle')}</p>

        {/* What are you selling, where, how much */}
        <div className="farm-card mt-5 space-y-4 p-4">
          <div className="flex flex-wrap gap-2">
            {(districtInfo?.crops ?? []).map(({ crop: c }) => {
              const active = c === crop;
              return (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCrop(c as CropId)}
                  className="farm-focus flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold"
                  style={{
                    borderColor: active ? 'var(--leaf)' : 'var(--farm-line)',
                    background: active ? 'var(--leaf-wash)' : 'var(--farm-paper)',
                    color: active ? 'var(--leaf-deep)' : 'var(--farm-ink-soft)',
                  }}
                >
                  <ProduceIcon name={c} size="sm" plated={false} />
                  {produceScript(resolveProduce(c), lang).text}
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-[1fr_auto] items-end gap-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold text-[var(--farm-ink-faint)]">{tri(lang, 'Your mandi', 'ನಿಮ್ಮ ಮಂಡಿ', 'आपकी मंडी')}</span>
              <select
                value={activeMandi ?? ''}
                onChange={(e) => setMandi(e.target.value)}
                className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold text-[var(--farm-ink)]"
              >
                {mandis.map((m) => (
                  <option key={m.id} value={m.id}>{placeName(m, lang)}</option>
                ))}
              </select>
            </label>

            <div>
              <span className="mb-1.5 block text-xs font-bold text-[var(--farm-ink-faint)]">{tri(lang, 'Quintals', 'ಕ್ವಿಂಟಾಲ್', 'क्विंटल')}</span>
              <div className="flex items-center rounded-xl border border-[var(--farm-line)] bg-white">
                <button type="button" aria-label="Less" onClick={() => setQuantity(Math.max(1, quantity - 5))} className="farm-focus flex h-11 w-11 items-center justify-center rounded-l-xl text-[var(--farm-ink-soft)] hover:bg-[var(--farm-paper-warm)]"><Minus className="h-4 w-4" /></button>
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
                  className="w-14 bg-transparent text-center text-base font-bold tabular-nums text-[var(--farm-ink)] outline-none"
                  aria-label="Quintals"
                />
                <button type="button" aria-label="More" onClick={() => setQuantity(quantity + 5)} className="farm-focus flex h-11 w-11 items-center justify-center rounded-r-xl text-[var(--farm-ink-soft)] hover:bg-[var(--farm-paper-warm)]"><Plus className="h-4 w-4" /></button>
              </div>
            </div>
          </div>
        </div>

        {isFetching && !plan && (
          <div className="mt-10 flex items-center justify-center gap-2 text-sm text-[var(--farm-ink-faint)]"><Loader2 className="h-4 w-4 animate-spin" /> …</div>
        )}

        {plan?.status === 'UNAVAILABLE' && <div className="mt-6"><UnavailableNotice reason={plan.reason} /></div>}

        {plan?.status === 'OK' && best && (
          <motion.div key={`${crop}-${activeMandi}-${quantity}`} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}>
            {/* The answer */}
            <section className="farm-card mt-6 overflow-hidden">
              <div className="h-2 bg-[var(--leaf)]" />
              <div className="p-6">
                <p className="text-sm font-semibold text-[var(--leaf-deep)]">{t('sellplan.best_plan')}</p>
                <h2 className="farm-display mt-1 text-3xl leading-tight text-[var(--farm-ink)]">{label(best)}</h2>
                <p className="mt-1 text-base font-semibold text-[var(--farm-ink-soft)]">
                  {optionPlace(best, lang)}
                  {best.choice !== 'sell_today' && best.target_date ? ` · ${shortDate(best.target_date, lang)}` : ''}
                </p>
                <p className="farm-display mt-4 text-[2.75rem] leading-none tabular-nums text-[var(--leaf-deep)]">{rupees(best.total)}</p>
                {(plan.gain_vs_baseline ?? 0) > 0 && (
                  <p className="mt-1.5 text-sm font-bold text-[var(--leaf-deep)]">+{rupees(plan.gain_vs_baseline)} {t('sellplan.vs_selling_today')}</p>
                )}
                {best.choice === 'wait' && best.range_low != null && best.range_high != null && (
                  <p className="mt-2 text-sm tabular-nums text-[var(--farm-ink-soft)]">
                    {tri(lang, 'Likely between', 'ಸಂಭವನೀಯ ಶ್ರೇಣಿ', 'संभावित दायरा')} {rupees(best.range_low)} – {rupees(best.range_high)}
                  </p>
                )}
                {best.choice === 'travel' && best.distance_km != null && (
                  <p className="mt-2 text-sm text-[var(--farm-ink-soft)]">
                    {best.distance_km} km · {tri(lang, 'transport', 'ಸಾಗಣೆ', 'ढुलाई')} {rupees(best.transport_cost_per_quintal * quantity)} {tri(lang, 'already taken off', 'ಈಗಾಗಲೇ ಕಳೆಯಲಾಗಿದೆ', 'पहले ही घटाया गया')}
                  </p>
                )}
                {best.choice === 'wait' && <p className="mt-2 text-xs leading-relaxed text-[var(--farm-ink-faint)]">{t('sellplan.spoilage_note')}</p>}

                <button
                  type="button"
                  onClick={follow}
                  disabled={saved}
                  className="farm-focus mt-5 flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-base font-bold text-white disabled:opacity-80"
                  style={{ background: saved ? 'var(--farm-ink-soft)' : 'var(--leaf)' }}
                >
                  {saved ? <Check className="h-4 w-4" /> : <PiggyBank className="h-4 w-4" />}
                  {saved ? t('sellplan.saved_to_my_money') : t('sellplan.follow_this')}
                </button>
              </div>
            </section>

            {/* Every option on one scale */}
            <ul className="mt-5 space-y-3">
              {options.map((o, i) => {
                const Icon = ICON[o.choice];
                const isBest = o.choice === plan.best;
                return (
                  <li key={o.choice} className="farm-row p-4" style={isBest ? { borderColor: 'var(--leaf)' } : undefined}>
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="flex min-w-0 items-center gap-2 text-sm font-bold text-[var(--farm-ink)]">
                        <Icon className="h-4 w-4 shrink-0 text-[var(--farm-ink-soft)]" />
                        <span className="truncate">{label(o)} · {optionPlace(o, lang)}</span>
                      </p>
                      <p className="farm-display shrink-0 text-lg tabular-nums text-[var(--farm-ink)]">{rupees(o.total)}</p>
                    </div>
                    <div className="mt-2.5 h-2.5 overflow-hidden rounded-full bg-[var(--farm-line)]">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: isBest ? 'var(--leaf)' : 'var(--farm-ink-faint)' }}
                        initial={{ width: 0 }}
                        animate={{ width: `${(o.total / top) * 100}%` }}
                        transition={{ delay: 0.15 + i * 0.08, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                    <p className="mt-1.5 text-xs tabular-nums text-[var(--farm-ink-faint)]">
                      {rupees(o.price_per_quintal)} {say('unit.qtl', lang)}
                      {o.transport_cost_per_quintal > 0 && ` − ${rupees(o.transport_cost_per_quintal)} ${tri(lang, 'transport', 'ಸಾಗಣೆ', 'ढुलाई')}`}
                      {o.spoilage_pct ? ` − ${o.spoilage_pct}% ${tri(lang, 'spoilage', 'ಹಾಳಾಗುವಿಕೆ', 'खराबी')}` : ''}
                    </p>
                  </li>
                );
              })}
            </ul>

            {plan.call && plan.call.type !== 'ADVISED' && (
              <p className="mt-4 rounded-xl bg-[var(--farm-paper-warm)] p-3.5 text-sm leading-relaxed text-[var(--farm-ink-soft)]">
                {tri(
                  lang,
                  'We have no proven hold advice for this crop here, so waiting is not offered. The comparison is across mandis.',
                  'ಇಲ್ಲಿ ಈ ಬೆಳೆಗೆ ಸಾಬೀತಾದ ಇಡುವ ಸಲಹೆ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಕಾಯುವ ಆಯ್ಕೆ ಇಲ್ಲ. ಹೋಲಿಕೆ ಮಂಡಿಗಳ ನಡುವೆ ಮಾತ್ರ.',
                  'यहाँ इस फसल के लिए रोकने की साबित सलाह नहीं है, इसलिए रुकने का विकल्प नहीं दिया। तुलना मंडियों के बीच है।'
                )}
              </p>
            )}
          </motion.div>
        )}
      </main>
    </div>
  );
}
