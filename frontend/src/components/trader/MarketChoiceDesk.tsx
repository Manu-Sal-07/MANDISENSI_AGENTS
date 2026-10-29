'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Grid3x3 } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatRupees } from './shared';
import { marketChoiceApi } from '@/services/marketChoiceApi';

const SELECT =
  'rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground outline-none focus:ring-2 focus:ring-accent/30';
const HOLDS = [0, 1, 2, 3];
const VEHICLES = [
  { label: 'Shared truck · ₹0.35', rate: 0.35 },
  { label: 'Tempo · ₹0.70', rate: 0.7 },
  { label: 'Small pickup · ₹1.40', rate: 1.4 },
];
const ALPHAS = [
  { label: '80% floor', alpha: 0.2 },
  { label: '90% floor', alpha: 0.1 },
  { label: '95% floor', alpha: 0.05 },
];

/**
 * Market-Choice Desk: the whole action-value grid behind the farmer advice.
 *
 * Every cell is the expected net revenue per quintal of selling at that mandi
 * after that many days, from one origin, after transport, fee and spoilage; the
 * line under it is the conformal floor and the dot is the chance the mandi
 * reports on the sale day. Cells are shaded relative to the best cell, which is
 * outlined. A silent mandi is already priced in, because the model is trained on
 * what a farmer would actually have received (see /evidence).
 */
export default function MarketChoiceDesk() {
  const [crop, setCrop] = useState('tomato');
  const [origin, setOrigin] = useState('kolar');
  const [rate, setRate] = useState(0.7);
  const [alpha, setAlpha] = useState(0.1);

  const { data: info } = useQuery({ queryKey: ['mc-crops'], queryFn: () => marketChoiceApi.crops(), staleTime: 10 * 60 * 1000 });
  const { data, isFetching } = useQuery({
    queryKey: ['mc-matrix', crop, origin, alpha, rate],
    queryFn: () => marketChoiceApi.matrix(crop, { district: origin }, alpha, rate),
  });

  const rows = useMemo(() => [...(data?.mandis ?? [])].sort((a, b) => Math.max(...b.expected_net) - Math.max(...a.expected_net)), [data]);
  const [lo, hi] = useMemo(() => {
    const vals = rows.filter((r) => r.offered).flatMap((r) => r.expected_net);
    return vals.length ? [Math.min(...vals), Math.max(...vals)] : [0, 1];
  }, [rows]);

  return (
    <ToolCard
      title="Market-Choice Desk"
      subtitle="Expected net revenue per quintal for every mandi and holding period, with its guaranteed floor"
      icon={<Grid3x3 className="h-4.5 w-4.5" />}
      accent="#22d3ee"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className={`${SELECT} capitalize`}>
          {(info?.crops ?? [{ crop: 'tomato' }]).map((c) => (
            <option key={c.crop} value={c.crop}>{c.crop}</option>
          ))}
        </select>
        <select value={origin} onChange={(e) => setOrigin(e.target.value)} className={SELECT}>
          {(info?.origins ?? [{ id: 'kolar', name: 'Kolar' }]).map((o) => (
            <option key={o.id} value={o.id}>from {o.name}</option>
          ))}
        </select>
        <select value={rate} onChange={(e) => setRate(Number(e.target.value))} className={SELECT}>
          {VEHICLES.map((v) => (
            <option key={v.rate} value={v.rate}>{v.label}</option>
          ))}
        </select>
        <select value={alpha} onChange={(e) => setAlpha(Number(e.target.value))} className={SELECT}>
          {ALPHAS.map((a) => (
            <option key={a.alpha} value={a.alpha}>{a.label}</option>
          ))}
        </select>
      </div>

      {isFetching && <LoadingRow label="Pricing every mandi and hold…" />}
      {!isFetching && data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {!isFetching && data?.status === 'OK' && (
        <div className="space-y-3">
          <p className="text-[11px] text-neutral-signal">
            Decision day {data.decision_day} · prices through {data.as_of} · error multiplier {data.error_scale?.multiplier} · transport ₹
            {data.assumptions?.transport_per_q_km}/q/km · spoilage {((data.assumptions?.spoilage_per_day ?? 0) * 100).toFixed(1)}%/day
          </p>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full min-w-[560px] border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="px-3 py-2 text-left font-bold">Mandi</th>
                  <th className="px-2 py-2 text-right font-bold">km</th>
                  <th className="px-2 py-2 text-right font-bold">last ₹</th>
                  {HOLDS.map((h) => (
                    <th key={h} className="px-2 py-2 text-center font-bold">{h === 0 ? 'sell today' : `+${h} day${h > 1 ? 's' : ''}`}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.mandi_id} className="border-t border-border" style={{ opacity: r.offered ? 1 : 0.4 }}>
                    <td className="px-3 py-2 font-bold text-foreground">
                      {r.mandi_name}
                      {!r.offered && <span className="ml-1.5 text-[10px] font-semibold text-amber-500">silent {r.days_since_report}d</span>}
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums text-neutral-signal">{r.distance_km}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-neutral-signal">{formatRupees(r.last_price)}</td>
                    {HOLDS.map((h) => {
                      const v = r.expected_net[h];
                      const t = hi > lo ? (v - lo) / (hi - lo) : 0;
                      const isBest = data.best?.mandi_id === r.mandi_id && data.best?.hold_days === h;
                      return (
                        <td
                          key={h}
                          className="px-2 py-1.5 text-center"
                          style={{
                            background: r.offered ? `color-mix(in oklch, var(--bullish) ${Math.round(t * 55)}%, transparent)` : undefined,
                            outline: isBest ? '2px solid var(--bullish)' : undefined,
                            outlineOffset: '-2px',
                          }}
                          title={`Expected price ${formatRupees(r.expected_price[h])} · floor ${formatRupees(r.floor[h])} · open ${Math.round(r.chance_open[h] * 100)}%`}
                        >
                          <div className="font-mono text-[13px] font-bold tabular-nums text-foreground">{formatRupees(v)}</div>
                          <div className="font-mono text-[10px] tabular-nums text-neutral-signal">≥ {formatRupees(r.floor[h])}</div>
                          <div className="mt-0.5 flex items-center justify-center gap-1 text-[9px] text-neutral-signal">
                            <span
                              className="inline-block h-1.5 w-1.5 rounded-full"
                              style={{ background: r.chance_open[h] > 0.8 ? 'var(--bullish)' : r.chance_open[h] > 0.5 ? '#f59e0b' : 'var(--bearish, #ef4444)' }}
                            />
                            {Math.round(r.chance_open[h] * 100)}% open
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {data.farm_gate && (
                  <tr className="border-t border-border bg-surface-2/60">
                    <td className="px-3 py-2 font-bold text-foreground">Farm gate</td>
                    <td className="px-2 py-2 text-right text-neutral-signal">0</td>
                    <td className="px-2 py-2" />
                    <td className="px-2 py-2 text-center" colSpan={4}>
                      <span className="font-mono text-[13px] font-bold tabular-nums text-foreground">{formatRupees(data.farm_gate.expected_net)}</span>
                      <span className="ml-2 font-mono text-[10px] text-neutral-signal">≥ {formatRupees(data.farm_gate.floor)}</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] leading-relaxed text-neutral-signal">
            Hover a cell for the expected price. The green outline is the recommended action; the floor under each cell is violated about{' '}
            {Math.round((alpha ?? 0.1) * 100)}% of the time in walk-forward tests. Mandis silent for more than 14 days are not offered.
          </p>
        </div>
      )}
    </ToolCard>
  );
}
