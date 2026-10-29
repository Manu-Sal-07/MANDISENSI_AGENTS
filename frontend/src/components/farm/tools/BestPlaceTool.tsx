'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowRight, BadgeCheck, CalendarDays, Crown, Loader2, Navigation, ShieldCheck, Truck } from 'lucide-react';

import ToolSheet from './ToolSheet';
import AdviceInsight from './AdviceInsight';
import { QuantityPicker } from './ContextPicker';
import ProduceIcon, { resolveProduce, produceScript } from '../ProduceIcon';
import { useToolSelection } from '@/context/ToolContext';
import { useLanguage } from '@/context/LanguageContext';
import { marketChoiceApi, type McOption } from '@/services/marketChoiceApi';
import { formatRupees } from '@/lib/format';
import { dayLabel, mandiLabel, mc } from '@/lib/i18n/marketChoiceCopy';
import type { Lang } from '@/lib/i18n/translations';

const ALPHAS: Array<{ alpha: number; pct: string }> = [
  { alpha: 0.2, pct: '80%' },
  { alpha: 0.1, pct: '90%' },
  { alpha: 0.05, pct: '95%' },
];
const VEHICLES: Array<{ key: string; rate: number }> = [
  { key: 'shared_truck', rate: 0.35 },
  { key: 'tempo', rate: 0.7 },
  { key: 'small_pickup', rate: 1.4 },
];
const STORAGE_KEY = 'mandisense-best-place-v1';

const placeName = (d: { name: string; name_kn: string; name_hi: string }, lang: Lang) =>
  lang === 'kn' ? d.name_kn : lang === 'hi' ? d.name_hi : d.name;

const chip = (active: boolean): React.CSSProperties => ({
  borderColor: active ? 'var(--leaf)' : 'var(--farm-line)',
  background: active ? 'var(--leaf-wash)' : 'var(--farm-paper)',
  color: active ? 'var(--leaf-deep)' : 'var(--farm-ink-soft)',
});

function whenText(o: McOption, lang: Lang): string {
  const date = new Date(o.sale_date).toLocaleDateString(lang === 'en' ? 'en-IN' : lang === 'kn' ? 'kn-IN' : 'hi-IN', { weekday: 'long', day: 'numeric', month: 'short' });
  return `${date} · ${dayLabel(o.hold_days, lang)}`;
}

export default function BestPlaceTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, setCommodity, quantityQuintals } = useToolSelection();
  const { lang } = useLanguage();
  const [district, setDistrict] = useState('kolar');
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [vehicle, setVehicle] = useState('tempo');
  const [alpha, setAlpha] = useState(0.1);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        if (s.district) setDistrict(s.district);
        if (s.vehicle) setVehicle(s.vehicle);
        if (s.alpha) setAlpha(s.alpha);
      }
    } catch {
      /* start from the defaults */
    }
  }, []);
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ district, vehicle, alpha }));
    } catch {
      /* losing the preference is fine */
    }
  }, [district, vehicle, alpha]);

  const { data: info } = useQuery({ queryKey: ['mc-crops'], queryFn: () => marketChoiceApi.crops(), staleTime: 10 * 60 * 1000, enabled: open });
  const served = useMemo(() => (info?.crops ?? []).map((c) => c.crop), [info]);
  const crop = served.length && !served.includes(commodity) ? served[0] : commodity;
  const rate = VEHICLES.find((v) => v.key === vehicle)?.rate ?? 0.7;
  const origin = coords ? { lat: coords.lat, lon: coords.lon } : { district };

  const { data, isFetching, isError } = useQuery({
    queryKey: ['mc-recommend', crop, origin, quantityQuintals, alpha, rate],
    queryFn: () => marketChoiceApi.recommend(crop, origin, quantityQuintals, alpha, rate),
    enabled: open && served.length > 0,
  });

  const useMyLocation = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setCoords({ lat: p.coords.latitude, lon: p.coords.longitude });
        setLocating(false);
      },
      () => setLocating(false),
      { timeout: 8000 }
    );
  };

  const rec = data?.recommended;
  const ev = data?.evidence;
  const isGate = rec?.kind === 'farm_gate';
  const violation = data?.guarantee?.backtest_violation;
  const moneyDelta = (n: number | null | undefined) =>
    n === null || n === undefined ? null : `${formatRupees(Math.abs(n))} ${n >= 0 ? mc('more', lang) : mc('less', lang)}`;

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title={mc('title', lang)}
      subtitle={mc('subtitle', lang)}
      accentColour="#0b6e4f"
      icon={<ShieldCheck className="h-5 w-5" />}
    >
      <div className="space-y-4">
        {/* crop */}
        <div className="flex flex-wrap gap-2">
          {served.map((c) => {
            const produce = resolveProduce(c);
            const script = produceScript(produce, lang);
            return (
              <button
                key={c}
                type="button"
                onClick={() => setCommodity(c)}
                className="farm-focus flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold transition-colors"
                style={chip(crop === c)}
              >
                <ProduceIcon name={c as never} size="sm" plated={false} />
                <span>{script.text || produce.label}</span>
              </button>
            );
          })}
        </div>

        {/* where, how much, how carried */}
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('where_are_you', lang)}</span>
            <select
              value={coords ? '__gps__' : district}
              onChange={(e) => {
                setCoords(null);
                setDistrict(e.target.value);
              }}
              className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold text-[var(--farm-ink)]"
            >
              {coords && <option value="__gps__">{mc('located', lang)}</option>}
              {(info?.origins ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {placeName(o, lang)}
                </option>
              ))}
            </select>
          </label>
          <QuantityPicker />
        </div>
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="farm-focus farm-tap flex w-full items-center justify-center gap-1.5 rounded-xl border border-[var(--farm-line)] bg-white text-sm font-bold text-[var(--leaf)] disabled:opacity-50"
        >
          {locating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Navigation className="h-4 w-4" />}
          {coords ? mc('located', lang) : mc('use_location', lang)}
        </button>

        <div>
          <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('vehicle', lang)}</span>
          <div className="flex flex-wrap gap-2">
            {VEHICLES.map((v) => (
              <button
                key={v.key}
                type="button"
                onClick={() => setVehicle(v.key)}
                className="farm-focus flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold"
                style={chip(vehicle === v.key)}
              >
                <Truck className="h-3.5 w-3.5" /> {mc(`veh.${v.key}`, lang)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('sure', lang)}</span>
          <div className="flex gap-2">
            {ALPHAS.map((a) => (
              <button
                key={a.alpha}
                type="button"
                onClick={() => setAlpha(a.alpha)}
                className="farm-focus rounded-full border px-4 py-1.5 text-sm font-bold"
                style={chip(alpha === a.alpha)}
              >
                {a.pct}
              </button>
            ))}
          </div>
        </div>

        {(isFetching || (!data && !isError && open)) && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> {mc('loading', lang)}
          </div>
        )}

        {!isFetching && (isError || data?.status === 'UNAVAILABLE') && (
          <div className="flex items-start gap-3 rounded-2xl border border-amber-900/15 bg-amber-50 px-4 py-4">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div>
              <p className="text-sm font-bold text-amber-900">{mc('unavailable', lang)}</p>
              {data?.reason && <p className="mt-1 text-sm leading-relaxed text-amber-800/80">{data.reason}</p>}
            </div>
          </div>
        )}

        {!isFetching && data?.status === 'OK' && rec && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            {/* the answer */}
            <div className="rounded-3xl border-2 p-5" style={{ borderColor: 'var(--leaf)', background: 'var(--leaf-wash)' }}>
              <p className="flex items-center gap-1.5 text-xs font-black uppercase tracking-[0.14em]" style={{ color: 'var(--leaf-deep)' }}>
                <Crown className="h-3.5 w-3.5" /> {isGate ? mc('sell_farm_gate', lang) : mc('sell_at', lang)}
              </p>
              <p className="mt-1 text-2xl font-black leading-tight text-[var(--farm-ink)]">
                {isGate ? mc('sell_farm_gate', lang) : mandiLabel(rec, lang)}
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-[var(--farm-ink-soft)]">
                <CalendarDays className="h-4 w-4" /> {whenText(rec, lang)}
                {!isGate && <span className="text-[var(--farm-ink-faint)]">· {mc('distance', lang, { n: rec.distance_km })}</span>}
              </p>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-white/80 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('expected', lang)}</p>
                  <p className="mt-0.5 font-mono text-2xl font-black text-[var(--farm-ink)]">{formatRupees(rec.expected_net_per_q)}</p>
                  <p className="text-[11px] text-[var(--farm-ink-faint)]">{mc('per_q', lang)}</p>
                </div>
                <div className="rounded-2xl bg-white p-3 ring-2" style={{ ['--tw-ring-color' as string]: 'var(--leaf)' }}>
                  <p className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: 'var(--leaf-deep)' }}>
                    <BadgeCheck className="h-3.5 w-3.5" /> {mc('floor', lang)}
                  </p>
                  <p className="mt-0.5 font-mono text-2xl font-black" style={{ color: 'var(--leaf-deep)' }}>{formatRupees(rec.floor_per_q)}</p>
                  <p className="text-[11px] text-[var(--farm-ink-faint)]">{mc('per_q', lang)}</p>
                </div>
              </div>

              <p className="mt-3 text-xs leading-relaxed text-[var(--farm-ink-soft)]">
                {mc('total', lang, { q: data.quantity_quintals ?? quantityQuintals })}:{' '}
                <b>{formatRupees(rec.total_expected)}</b> {mc('expected_total', lang)} · <b>{formatRupees(rec.total_floor)}</b> {mc('floor_total', lang)}
              </p>
              {violation !== null && violation !== undefined && (
                <p className="mt-1 text-[11px] text-[var(--farm-ink-faint)]">
                  {data.confidence_pct}% — {mc('floor.note', lang, { p: `${Math.round(violation * 100)}%` })}
                </p>
              )}
              {!isGate && (
                <p className="mt-2 text-xs font-semibold text-[var(--farm-ink-soft)]">
                  {mc('chance_open', lang)}: {Math.round(rec.chance_open * 100)}%
                </p>
              )}
            </div>

            {/* comparison with the obvious alternative */}
            {data.baselines?.nearest_today && data.gain?.vs_nearest_per_q !== null && (
              <div className="rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3 text-sm">
                <p className="text-[var(--farm-ink-soft)]">
                  <b className="font-mono" style={{ color: (data.gain?.vs_nearest_per_q ?? 0) >= 0 ? 'var(--leaf-deep)' : 'var(--tomato)' }}>
                    {moneyDelta(data.gain?.vs_nearest_per_q)}
                  </b>{' '}
                  {mc('per_q', lang)} {mc('vs_nearest', lang)} ({mandiLabel(data.baselines.nearest_today, lang)})
                  {data.gain?.vs_nearest_total != null && Math.abs(data.gain.vs_nearest_total) >= 1 && (
                    <> — <b className="font-mono">{moneyDelta(data.gain.vs_nearest_total)}</b></>
                  )}
                </p>
              </div>
            )}

            {data.caveats && data.caveats.length > 0 && (
              <div className="space-y-1.5">
                {data.caveats.map((c) => (
                  <p key={c} className="flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" /> {mc(`caveat.${c}`, lang)}
                  </p>
                ))}
              </div>
            )}

            {data.safest && (
              <div className="rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3">
                <p className="text-sm font-bold text-[var(--farm-ink)]">{mc('safest', lang)}</p>
                <p className="mt-0.5 text-sm text-[var(--farm-ink-soft)]">
                  {mandiLabel(data.safest, lang)} · {whenText(data.safest, lang)}: {mc('floor', lang)}{' '}
                  <b className="font-mono">{formatRupees(data.safest.floor_per_q)}</b> {mc('per_q', lang)}
                </p>
                <p className="mt-0.5 text-[11px] text-[var(--farm-ink-faint)]">{mc('safest.note', lang)}</p>
              </div>
            )}

            {/* other options */}
            {(data.alternatives ?? []).length > 0 && (
              <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('others', lang)}</p>
                <div className="space-y-1.5">
                  {(data.alternatives ?? []).map((o, i) => (
                    <div key={`${o.mandi_id}-${o.hold_days}-${i}`} className="flex items-center justify-between rounded-xl border border-[var(--farm-line)] bg-[var(--farm-paper)] px-3 py-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-[var(--farm-ink)]">{o.kind === 'farm_gate' ? mc('sell_farm_gate', lang) : mandiLabel(o, lang)}</p>
                        <p className="text-[11px] text-[var(--farm-ink-faint)]">
                          {dayLabel(o.hold_days, lang)}
                          {o.kind === 'mandi' && <> · {Math.round(o.chance_open * 100)}% {mc('chance_open', lang).toLowerCase()}</>}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm font-black text-[var(--farm-ink)]">{formatRupees(o.expected_net_per_q)}</p>
                        <p className="font-mono text-[11px]" style={{ color: 'var(--leaf-deep)' }}>≥ {formatRupees(o.floor_per_q)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <AdviceInsight crop={crop} origin={origin} quantity={data.quantity_quintals ?? quantityQuintals} alpha={alpha} rate={rate} lang={lang} />

            {/* track record, stated honestly */}
            {ev?.status === 'OK' && ev.mean_net_revenue && (
              <div className="rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3">
                <p className="text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">{mc('track', lang)}</p>
                <p className="mt-1 text-sm leading-relaxed text-[var(--farm-ink-soft)]">
                  {mc('track.line', lang, {
                    d: ev.scored_days ?? '',
                    a: formatRupees(ev.mean_net_revenue.recommended),
                    b: formatRupees(ev.mean_net_revenue.nearest),
                  })}
                </p>
                {ev.level === 'limited' ? (
                  <p className="mt-1.5 text-xs font-semibold text-amber-800">{mc('track.limited', lang)}</p>
                ) : (
                  ev.gain_vs_highest_yesterday && (
                    <p className="mt-1.5 text-xs font-semibold" style={{ color: 'var(--leaf-deep)' }}>
                      {mc('track.gain', lang, { g: formatRupees(ev.gain_vs_highest_yesterday.mean) })}
                    </p>
                  )
                )}
                <Link href="/evidence" onClick={onClose} className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-[var(--leaf)]">
                  {mc('why', lang)} <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            )}

            {data.assumptions && (
              <p className="text-[11px] leading-relaxed text-[var(--farm-ink-faint)]">
                {mc('assume', lang, { t: data.assumptions.transport_per_q_km, s: (data.assumptions.spoilage_per_day * 100).toFixed(1) })}
                {data.as_of && <> {mc('asof', lang, { d: data.as_of })}.</>}
              </p>
            )}
          </motion.div>
        )}
      </div>
    </ToolSheet>
  );
}
