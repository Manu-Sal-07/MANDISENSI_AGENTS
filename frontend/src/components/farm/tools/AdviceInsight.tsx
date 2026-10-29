'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Bot, ChevronDown, Eye, Loader2, Sparkles } from 'lucide-react';

import { shockApi, type ShockItem } from '@/services/shockApi';
import { sc } from '@/lib/i18n/shockCopy';
import { resolveProduce, produceScript } from '../ProduceIcon';
import type { Lang } from '@/lib/i18n/translations';

interface Origin {
  district?: string;
  lat?: number;
  lon?: number;
}

interface Props {
  crop: string;
  origin: Origin;
  quantity: number;
  alpha: number;
  rate: number;
  lang: Lang;
}

const CARD = 'rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3';
const HEAD = 'text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]';

/**
 * "Why this advice" and the supply watch, shown under the sell recommendation.
 *
 * The reasons are fetched only when the farmer opens the panel (the wording can
 * involve a language model, so it is never on the critical path of the advice).
 * The text is composed server-side: figures, names and dates are inserted by
 * code, and the panel states who worded it. The supply watch reports what is
 * observed (arrivals against normal, the neighbour price gap) and makes a price
 * claim only when the server sends one, which it does for ROBUST evidence alone.
 */
export default function AdviceInsight({ crop, origin, quantity, alpha, rate, lang }: Props) {
  const [open, setOpen] = useState(false);

  const watch = useQuery({
    queryKey: ['shock-farmer', crop, origin.district],
    queryFn: () => shockApi.radar('farmer', crop, origin.district),
    enabled: Boolean(origin.district),
    staleTime: 10 * 60 * 1000,
  });
  const why = useQuery({
    queryKey: ['mc-explain', crop, origin, quantity, alpha, rate, lang],
    queryFn: () => shockApi.explain(crop, origin, quantity, alpha, rate, lang),
    enabled: open,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  const item = watch.data?.status === 'OK' ? watch.data.items[0] : undefined;
  const ex = why.data?.status === 'OK' ? why.data.explanation : undefined;

  return (
    <>
      {item && <SupplyWatch item={item} lang={lang} />}

      <div className={CARD}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="farm-focus flex w-full items-center justify-between gap-2 text-left"
        >
          <span className="flex items-center gap-2 text-sm font-bold text-[var(--farm-ink)]">
            <Sparkles className="h-4 w-4" style={{ color: 'var(--leaf)' }} /> {open ? sc('why.title', lang) : sc('why.show', lang)}
          </span>
          <ChevronDown className={`h-4 w-4 text-[var(--farm-ink-faint)] transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>

        {open && (
          <div className="mt-3 space-y-3">
            {why.isFetching && (
              <p className="flex items-center gap-2 text-sm text-[var(--farm-ink-soft)]">
                <Loader2 className="h-4 w-4 animate-spin" /> {sc('why.loading', lang)}
              </p>
            )}
            {!why.isFetching && !ex && <p className="text-sm text-[var(--farm-ink-soft)]">{sc('why.unavailable', lang)}</p>}
            {!why.isFetching && ex && (
              <>
                <ul className="space-y-2">
                  {ex.why.map((line, i) => (
                    <li key={i} className="flex gap-2 text-sm leading-relaxed text-[var(--farm-ink)]">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: 'var(--leaf)' }} />
                      {line}
                    </li>
                  ))}
                </ul>
                {ex.cautions.length > 0 && (
                  <div className="rounded-xl bg-amber-50 px-3 py-2">
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-amber-900">{sc('why.cautions', lang)}</p>
                    {ex.cautions.map((line, i) => (
                      <p key={i} className="flex gap-2 text-xs leading-relaxed text-amber-900">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {line}
                      </p>
                    ))}
                  </div>
                )}
                <p className="flex items-start gap-1.5 text-[11px] leading-relaxed text-[var(--farm-ink-faint)]">
                  <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {sc(ex.author === 'llm' ? 'why.author.llm' : 'why.author.rules', lang)}
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}

function SupplyWatch({ item, lang }: { item: ShockItem; lang: Lang }) {
  const produce = resolveProduce(item.crop);
  const cropName = produceScript(produce, lang).text || produce.label;
  const a = item.arrivals;
  const tone = a.state === 'glut' ? '#b45309' : a.state === 'squeeze' ? '#1d4ed8' : 'var(--leaf-deep)';
  const gap = item.gap;
  const gapDir = gap && gap.neighbours_dearer_by_pct >= 0 ? 'more' : 'less';

  return (
    <div className={CARD}>
      <p className={`${HEAD} flex items-center gap-1.5`}>
        <Eye className="h-3.5 w-3.5" /> {sc('watch.title', lang)}
      </p>

      <div className="mt-2">
        <p className="text-xs text-[var(--farm-ink-soft)]">{sc('watch.arrivals', lang, { place: item.district_name })}</p>
        <p className="mt-0.5 text-base font-bold" style={{ color: tone }}>
          {sc(`watch.${a.state}`, lang)}
          <span className="ml-2 text-xs font-semibold text-[var(--farm-ink-faint)]">{sc('watch.times', lang, { x: a.times_normal.toFixed(1) })}</span>
        </p>
        {a.age_days > 3 && <p className="mt-1 text-[11px] text-amber-800">{sc('watch.stale', lang, { n: a.age_days })}</p>}
      </div>

      {gap && Math.abs(gap.neighbours_dearer_by_pct) >= 5 && (
        <div className="mt-3 border-t border-[var(--farm-line)] pt-3">
          <p className="text-sm font-semibold text-[var(--farm-ink)]">
            {sc('watch.gap', lang, {
              p: Math.abs(Math.round(gap.neighbours_dearer_by_pct)),
              dir: sc(`watch.${gapDir}`, lang),
              place: item.district_name,
              crop: cropName,
            })}
          </p>
          {gap.median_half_life_weeks !== null && gap.pairs_closing === gap.pairs_tested && (
            <p className="mt-1 text-[11px] leading-relaxed text-[var(--farm-ink-faint)]">
              {sc('watch.gapnote', lang, { w: Math.max(1, Math.round(gap.median_half_life_weeks * 2)) })}
            </p>
          )}
        </div>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-[var(--farm-ink-faint)]">
        {item.response && item.response.tier === 'ROBUST'
          ? sc('watch.robust', lang, { p: Math.abs(item.response.typical_change_pct), d: item.response.horizon_days })
          : sc('watch.noclaim', lang)}
      </p>
    </div>
  );
}
