'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Loader2, Scale } from 'lucide-react';

import { marketChoiceApi, type McBreakdownOption, type McOrigin } from '@/services/marketChoiceApi';
import { formatRupees } from '@/lib/format';
import { dayLabel, mandiLabel, mc } from '@/lib/i18n/marketChoiceCopy';
import type { Lang } from '@/lib/i18n/translations';

const CARD = 'rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3';
const HEAD = 'text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]';

/** Colours of the cost parts; the share a farmer keeps is the leaf green. */
const PART_COLOUR: Record<string, string> = {
  net: 'var(--leaf)',
  fee: '#d9a441',
  spoilage: '#d9742b',
  transport: '#3b82c4',
  handling: '#8a8f98',
  farm_gate_discount: '#c0392b',
};
const PART_ORDER = ['fee', 'spoilage', 'transport', 'handling', 'farm_gate_discount'] as const;

interface Props {
  crop: string;
  origin: McOrigin;
  quantity: number;
  alpha: number;
  rate: number;
  lang: Lang;
}

function Row({ name, opt, lang, scale, label }: { name: string; opt: McBreakdownOption; lang: Lang; scale: number; label: string }) {
  const price = opt.parts.find((p) => p.key === 'price')?.value ?? 0;
  const costs = PART_ORDER.map((k) => ({ key: k, value: -(opt.parts.find((p) => p.key === k)?.value ?? 0) })).filter((c) => c.value > 0.5);
  const o = opt.option;
  const place = o.kind === 'farm_gate' ? mc('why.row.farm_gate', lang) : mandiLabel(o, lang);
  return (
    <div className="py-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 truncate text-sm font-bold text-[var(--farm-ink)]">
          {label}
          {o.kind === 'mandi' && <span className="font-semibold text-[var(--farm-ink-soft)]"> · {place}, {dayLabel(o.hold_days, lang)}</span>}
        </p>
        <p className="shrink-0 font-mono text-base font-black" style={{ color: name === 'recommended' ? 'var(--leaf-deep)' : 'var(--farm-ink)' }}>
          {formatRupees(opt.net)}
        </p>
      </div>
      <div className="mt-1.5 flex h-3.5 overflow-hidden rounded-full bg-[var(--farm-line)]" style={{ width: `${Math.max(8, (price / scale) * 100)}%` }}
        role="img" aria-label={`${formatRupees(opt.net)}`}>
        <div style={{ width: `${(opt.net / Math.max(price, 1)) * 100}%`, background: PART_COLOUR.net }} />
        {costs.map((c) => (
          <div key={c.key} title={`${mc(`why.${c.key}`, lang)}: ${formatRupees(c.value)}`} style={{ width: `${(c.value / Math.max(price, 1)) * 100}%`, background: PART_COLOUR[c.key] }} />
        ))}
      </div>
      <p className="mt-1 text-[11px] tabular-nums text-[var(--farm-ink-faint)]">
        {mc('why.price', lang)} {formatRupees(price)}
        {costs.map((c) => ` − ${mc(`why.${c.key}`, lang).toLowerCase()} ${formatRupees(c.value)}`).join('')}
      </p>
    </div>
  );
}

/**
 * "Why this mandi?": the arithmetic behind the advice, per quintal, for the recommendation and the choices a farmer
 * would otherwise make. Fetched only when opened. The parts add up exactly to the net figure the advice shows.
 */
export default function WhyThisMandi({ crop, origin, quantity, alpha, rate, lang }: Props) {
  const [open, setOpen] = useState(false);
  const { data, isFetching } = useQuery({
    queryKey: ['mc-breakdown', crop, origin, quantity, alpha, rate],
    queryFn: () => marketChoiceApi.breakdown(crop, origin, quantity, alpha, rate),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  });

  const opts = data?.status === 'OK' ? data.options : undefined;
  const rows = opts
    ? (['recommended', 'nearest_today', 'highest_yesterday', 'farm_gate'] as const).filter((k, i, all) => {
        if (k === 'recommended') return true;
        const sig = (x: (typeof all)[number]) => `${opts[x].option.mandi_id}-${opts[x].option.hold_days}`;
        return !all.slice(0, i).some((p) => sig(p) === sig(k));        // do not show the same action twice
      })
    : [];
  const scale = opts ? Math.max(...rows.map((k) => opts[k].parts.find((p) => p.key === 'price')?.value ?? 0), 1) : 1;

  return (
    <div className={CARD}>
      <button type="button" onClick={() => setOpen((v) => !v)} className="farm-focus flex w-full items-center justify-between gap-2" aria-expanded={open}>
        <span className="flex items-center gap-2 text-sm font-bold text-[var(--farm-ink)]">
          <Scale className="h-4 w-4 text-[var(--leaf)]" /> {mc('why.title', lang)}
        </span>
        <ChevronDown className={`h-4 w-4 text-[var(--farm-ink-faint)] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-2">
          <p className={HEAD}>{mc('why.sub', lang)}</p>
          {isFetching && !data && <div className="flex items-center gap-2 py-4 text-sm text-[var(--farm-ink-faint)]"><Loader2 className="h-4 w-4 animate-spin" /> {mc('loading', lang)}</div>}
          {data?.status === 'UNAVAILABLE' && <p className="py-3 text-sm text-[var(--farm-ink-soft)]">{data.reason}</p>}
          {opts && (
            <>
              <div className="divide-y divide-[var(--farm-line)]">
                {rows.map((k) => <Row key={k} name={k} opt={opts[k]} lang={lang} scale={scale} label={mc(`why.row.${k}`, lang)} />)}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                {(['net', ...PART_ORDER] as const).filter((k) => k === 'net' || rows.some((r) => opts[r].parts.some((p) => p.key === k && Math.abs(p.value) > 0.5))).map((k) => (
                  <span key={k} className="flex items-center gap-1 text-[11px] font-semibold text-[var(--farm-ink-soft)]">
                    <i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: PART_COLOUR[k] }} />
                    {k === 'net' ? mc('why.net', lang) : mc(`why.${k}`, lang)}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-[var(--farm-ink-faint)]">{mc('why.note', lang)}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
