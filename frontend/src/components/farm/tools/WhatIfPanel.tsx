'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Loader2, RotateCcw, SlidersHorizontal } from 'lucide-react';

import { marketChoiceApi, type McOrigin, type McPlace, type McSweep } from '@/services/marketChoiceApi';
import { formatRupees } from '@/lib/format';
import { dayLabel, mandiLabel, mc } from '@/lib/i18n/marketChoiceCopy';
import type { Lang } from '@/lib/i18n/translations';

const CARD = 'rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3';

interface Props {
  crop: string;
  origin: McOrigin;
  quantity: number;
  alpha: number;
  rate: number;
  lang: Lang;
}

const place = (p: McPlace, lang: Lang) => {
  const name = lang === 'kn' ? p.name_kn : lang === 'hi' ? p.name_hi : p.name;
  return p.mandi_id ? `${name} (${dayLabel(p.hold_days, lang)})` : name;
};

function useDebounced<T>(value: T, ms = 220): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

function Slider({ label, value, min, max, step, shown, onChange }: { label: string; value: number; min: number; max: number; step: number; shown: string; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-xs font-bold text-[var(--farm-ink-soft)]">
        <span>{label}</span>
        <span className="font-mono text-sm text-[var(--farm-ink)]">{shown}</span>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))}
        className="farm-focus mt-1 h-2 w-full cursor-pointer accent-[var(--leaf)]" aria-label={label} />
    </label>
  );
}

/** The first change of advice above the current setting of a swept cost, if there is one. */
const nextFlip = (sweep: McSweep | undefined, current: number) => sweep?.flips.find((f) => f.at > current);

/**
 * "What if my costs are different?": the farmer moves transport, spoilage and how long they can wait, and the advice is
 * re-priced under those costs at once. It also says the exact cost at which the advice would change, so the farmer can
 * see how safe the advice is to their own truck and crop.
 */
export default function WhatIfPanel({ crop, origin, quantity, alpha, rate, lang }: Props) {
  const [open, setOpen] = useState(false);
  const [transport, setTransport] = useState(rate);
  const [spoilage, setSpoilage] = useState<number | null>(null);
  const [maxHold, setMaxHold] = useState(3);
  useEffect(() => setTransport(rate), [rate]);

  const base = useQuery({
    queryKey: ['mc-sim-base', crop, origin, quantity, alpha, rate],
    queryFn: () => marketChoiceApi.simulate(crop, origin, quantity, { transport: rate }, alpha),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  });
  const defaultSpoilage = base.data?.defaults?.spoilage_per_day;
  useEffect(() => {
    if (defaultSpoilage !== undefined) setSpoilage((s) => s ?? defaultSpoilage);
  }, [defaultSpoilage]);

  const scenario = useDebounced({ transport, spoilage, maxHold });
  const sim = useQuery({
    queryKey: ['mc-sim', crop, origin, quantity, alpha, scenario],
    queryFn: () => marketChoiceApi.simulate(crop, origin, quantity, { transport: scenario.transport, spoilage: scenario.spoilage ?? undefined, maxHold: scenario.maxHold }, alpha),
    enabled: open && scenario.spoilage !== null,
    placeholderData: (prev) => prev,
  });

  const d = sim.data?.status === 'OK' ? sim.data : undefined;
  const rec = d?.recommended;
  const was = base.data?.status === 'OK' ? base.data.recommended : undefined;
  const changedFromStandard = useMemo(
    () => (rec && was ? rec.mandi_id !== was.mandi_id || rec.hold_days !== was.hold_days : false),
    [rec, was],
  );
  const tFlip = nextFlip(d?.sweeps?.transport, transport);
  const sFlip = nextFlip(d?.sweeps?.spoilage, spoilage ?? 0);
  const reset = () => {
    setTransport(rate);
    setSpoilage(defaultSpoilage ?? null);
    setMaxHold(3);
  };

  return (
    <div className={CARD}>
      <button type="button" onClick={() => setOpen((v) => !v)} className="farm-focus flex w-full items-center justify-between gap-2" aria-expanded={open}>
        <span className="flex items-center gap-2 text-sm font-bold text-[var(--farm-ink)]">
          <SlidersHorizontal className="h-4 w-4 text-[var(--leaf)]" /> {mc('whatif.title', lang)}
        </span>
        <ChevronDown className={`h-4 w-4 text-[var(--farm-ink-faint)] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-[var(--farm-ink-faint)]">{mc('whatif.sub', lang)}</p>
          {base.isFetching && !base.data && <div className="flex items-center gap-2 py-3 text-sm text-[var(--farm-ink-faint)]"><Loader2 className="h-4 w-4 animate-spin" /> {mc('loading', lang)}</div>}
          {base.data?.status === 'UNAVAILABLE' && <p className="text-sm text-[var(--farm-ink-soft)]">{base.data.reason}</p>}

          {base.data?.status === 'OK' && spoilage !== null && (
            <>
              <Slider label={mc('whatif.transport', lang)} value={transport} min={0.1} max={3} step={0.05} shown={`₹${transport.toFixed(2)}`} onChange={setTransport} />
              <Slider label={mc('whatif.spoilage', lang)} value={spoilage} min={0} max={0.08} step={0.0025} shown={`${(spoilage * 100).toFixed(1)}%`} onChange={setSpoilage} />
              <Slider label={mc('whatif.maxhold', lang)} value={maxHold} min={0} max={3} step={1} shown={dayLabel(maxHold, lang)} onChange={setMaxHold} />

              {rec && (
                <div className="rounded-xl p-3" style={{ background: changedFromStandard ? 'var(--turmeric-wash, #fdf3dc)' : 'var(--leaf-wash)' }} aria-live="polite">
                  <p className="text-[11px] font-black uppercase tracking-wide" style={{ color: changedFromStandard ? '#8a5a00' : 'var(--leaf-deep)' }}>
                    {changedFromStandard ? mc('whatif.changed', lang) : mc('whatif.same', lang)}
                  </p>
                  <p className="mt-0.5 text-lg font-black text-[var(--farm-ink)]">
                    {rec.kind === 'farm_gate' ? mc('sell_farm_gate', lang) : mandiLabel(rec, lang)}
                    {rec.kind === 'mandi' && <span className="text-sm font-semibold text-[var(--farm-ink-soft)]"> · {dayLabel(rec.hold_days, lang)}</span>}
                  </p>
                  <p className="mt-0.5 font-mono text-sm text-[var(--farm-ink)]">
                    {formatRupees(rec.expected_net_per_q)} {mc('per_q', lang)} · {mc('floor', lang)} {formatRupees(rec.floor_per_q)}
                  </p>
                  {changedFromStandard && was && (
                    <p className="mt-1 text-[11px] text-[var(--farm-ink-soft)]">
                      {mc('whatif.was', lang)}: {was.kind === 'farm_gate' ? mc('sell_farm_gate', lang) : mandiLabel(was, lang)}, {dayLabel(was.hold_days, lang)}
                    </p>
                  )}
                </div>
              )}

              <ul className="space-y-1 text-xs leading-relaxed text-[var(--farm-ink-soft)]">
                {tFlip ? (
                  <li>{mc('whatif.flip.transport', lang, { a: place(tFlip.from, lang), b: place(tFlip.to, lang), x: tFlip.at.toFixed(2) })}</li>
                ) : (
                  <li>{mc('whatif.stable.transport', lang)}</li>
                )}
                {sFlip && <li>{mc('whatif.flip.spoilage', lang, { a: place(sFlip.from, lang), b: place(sFlip.to, lang), x: (sFlip.at * 100).toFixed(1) })}</li>}
                <li className="text-[var(--farm-ink-faint)]">{mc('whatif.indicative', lang)}</li>
              </ul>

              <button type="button" onClick={reset} className="farm-focus flex items-center gap-1.5 text-xs font-bold text-[var(--leaf)]">
                <RotateCcw className="h-3.5 w-3.5" /> {mc('whatif.reset', lang)}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
