'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { UsersRound } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatRupees } from './shared';
import { marketChoiceApi, type McPlace } from '@/services/marketChoiceApi';

const SELECT =
  'rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground outline-none focus:ring-2 focus:ring-accent/30';
const CROWDS = [1, 10, 50, 200, 500, 1000, 2000, 5000];
const SHOWN = 8;

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

const place = (p: McPlace) => (p.mandi_id ? `${p.name}, ${p.hold_days === 0 ? 'today' : `+${p.hold_days}d`}` : p.name);

/**
 * Crowd Simulator: what if everyone follows the same advice?
 *
 * One recommendation is only good while few people take it. A yard's price falls when it receives more than its usual
 * daily arrivals: P(x) = P (1 + x / A)^(−b), with A the yard's median daily arrivals over the last year and b the price
 * flexibility. The default b = 0.115 is the within-mandi, within-month association of log price with log arrivals in the
 * tomato panel; it is an association, not a causal estimate, so it is offered as a slider. Three policies are compared with
 * the single farmer's advice: everyone takes the best action, everyone goes to the nearest yard, and a coordinated split
 * that maximises the group's total revenue (each farmer is advised an action with the probability shown).
 */
export default function CrowdSimulator() {
  const [crop, setCrop] = useState('tomato');
  const [origin, setOrigin] = useState('kolar');
  const [ci, setCi] = useState(3);
  const [qty, setQty] = useState(10);
  const [flex, setFlex] = useState(0.115);
  const q = useDebounced({ ci, qty, flex });

  const { data: info } = useQuery({ queryKey: ['mc-crops'], queryFn: () => marketChoiceApi.crops(), staleTime: 10 * 60 * 1000 });
  const { data, isFetching } = useQuery({
    queryKey: ['mc-crowd', crop, origin, q],
    queryFn: () => marketChoiceApi.crowd(crop, { district: origin }, CROWDS[q.ci], q.qty, q.flex),
    placeholderData: (prev) => prev,
  });
  const d = data?.status === 'OK' ? data : undefined;
  const bars = d
    ? [
        { label: 'One farmer alone', v: d.alone?.net_per_q ?? 0, c: '#94a3b8' },
        { label: 'Everyone follows the best action', v: d.everyone_follows_best?.net_per_q ?? 0, c: '#ef4444' },
        { label: 'Everyone goes to the nearest mandi', v: d.everyone_goes_nearest?.net_per_q ?? 0, c: '#f59e0b' },
        { label: 'Coordinated split', v: d.coordinated?.net_per_q ?? 0, c: '#22c55e' },
      ]
    : [];
  const top = Math.max(1, ...bars.map((b) => b.v));
  const rest = (d?.coordinated?.split ?? []).slice(SHOWN);

  return (
    <ToolCard
      title="Crowd Simulator"
      subtitle="Net revenue per quintal for each farmer when many farmers act on the same advice, and a split that avoids crashing one mandi"
      icon={<UsersRound className="h-4.5 w-4.5" />}
      accent="#a78bfa"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className={`${SELECT} capitalize`} aria-label="Crop">
          {(info?.crops ?? [{ crop: 'tomato' }]).map((c) => <option key={c.crop} value={c.crop}>{c.crop}</option>)}
        </select>
        <select value={origin} onChange={(e) => setOrigin(e.target.value)} className={SELECT} aria-label="Farmers' district">
          {(info?.origins ?? [{ id: 'kolar', name: 'Kolar' }]).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block text-xs font-semibold text-neutral-signal">
          Farmers following the advice: <b className="font-mono text-foreground">{CROWDS[ci].toLocaleString('en-IN')}</b>
          <input type="range" min={0} max={CROWDS.length - 1} step={1} value={ci} onChange={(e) => setCi(Number(e.target.value))} className="mt-1 w-full accent-violet-400" />
        </label>
        <label className="block text-xs font-semibold text-neutral-signal">
          Quintals each: <b className="font-mono text-foreground">{qty}</b>
          <input type="range" min={1} max={50} step={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} className="mt-1 w-full accent-violet-400" />
        </label>
        <label className="block text-xs font-semibold text-neutral-signal">
          Price flexibility b: <b className="font-mono text-foreground">{flex.toFixed(3)}</b>
          <input type="range" min={0} max={0.4} step={0.005} value={flex} onChange={(e) => setFlex(Number(e.target.value))} className="mt-1 w-full accent-violet-400" />
        </label>
      </div>

      {isFetching && !data && <LoadingRow label="Simulating the crowd…" />}
      {data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {d && (
        <div className="mt-5 space-y-5">
          <p className="text-xs leading-relaxed text-neutral-signal">
            Advice for one farmer: <b className="text-foreground">{d.recommended ? place(d.recommended) : '—'}</b>
            {d.recommended_yard_daily_arrivals_q ? <> · that yard usually receives about <b className="text-foreground">{Math.round(d.recommended_yard_daily_arrivals_q).toLocaleString('en-IN')}</b> quintals a day</> : null}
            {' '}· the crowd brings <b className="text-foreground">{(d.total_quintals ?? 0).toLocaleString('en-IN')}</b> quintals.
          </p>

          <div className="space-y-2.5">
            {bars.map((b) => (
              <div key={b.label}>
                <div className="flex items-baseline justify-between text-xs">
                  <span className="font-semibold text-foreground">{b.label}</span>
                  <span className="font-mono tabular-nums text-foreground">{formatRupees(b.v)}</span>
                </div>
                <div className="mt-1 h-3 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full rounded-full transition-all" style={{ width: `${(b.v / top) * 100}%`, background: b.c }} />
                </div>
              </div>
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-surface-2 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Price drop at the best yard</p>
              <p className="mt-0.5 font-mono text-xl font-black text-red-400">−{d.everyone_follows_best?.price_drop_pct ?? 0}%</p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Coordination gain per quintal</p>
              <p className="mt-0.5 font-mono text-xl font-black text-emerald-400">{formatRupees(d.gain_coordinated_vs_everyone_best_per_q)}</p>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Group gain in total</p>
              <p className="mt-0.5 font-mono text-xl font-black text-emerald-400">{formatRupees(d.gain_total_rs)}</p>
            </div>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-neutral-signal">Who is told what (coordinated split)</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="py-1.5">Advise</th><th className="py-1.5 text-right">Share of farmers</th><th className="py-1.5 text-right">Quintals</th>
                  <th className="py-1.5 text-right">Price drop there</th><th className="py-1.5 text-right">Net per quintal</th>
                </tr>
              </thead>
              <tbody>
                {(d.coordinated?.split ?? []).slice(0, SHOWN).map((s, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-1.5 font-semibold text-foreground">{place(s.label)}</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">{Math.round(s.share * 100)}%</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">{s.quintals.toLocaleString('en-IN')}</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">−{s.price_drop_pct}%</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">{formatRupees(s.net_per_q)}</td>
                  </tr>
                ))}
                {rest.length > 0 && (
                  <tr className="text-neutral-signal">
                    <td className="py-1.5">{rest.length} smaller actions</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">{Math.round(rest.reduce((a, r) => a + r.share, 0) * 100)}%</td>
                    <td className="py-1.5 text-right font-mono tabular-nums">{rest.reduce((a, r) => a + r.quintals, 0).toLocaleString('en-IN')}</td>
                    <td className="py-1.5 text-right">—</td><td className="py-1.5 text-right">—</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] leading-relaxed text-neutral-signal">
            Scenario, not a measurement: {d.flexibility_note} Move the flexibility slider to see how much the conclusion depends on it; at b = 0 the crowd costs nothing and every policy is equal.
          </p>
        </div>
      )}
    </ToolCard>
  );
}
