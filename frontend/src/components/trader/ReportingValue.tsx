'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Megaphone } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatRupees } from './shared';
import { marketChoiceApi } from '@/services/marketChoiceApi';

const SELECT =
  'rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground outline-none focus:ring-2 focus:ring-accent/30';
const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const CROPS = ['tomato', 'onion', 'potato', 'ginger', 'garlic'];

/** Silent share of a weekday as a colour: transparent when reliable, amber, then red when the mandi is effectively closed. */
const heat = (silent: number): string =>
  silent >= 0.9 ? 'rgba(239,68,68,0.85)' : silent >= 0.5 ? 'rgba(245,158,11,0.75)' : silent >= 0.2 ? 'rgba(245,158,11,0.35)' : 'rgba(34,197,94,0.35)';

/**
 * Silence Tax: what each mandi's unreliable reporting costs a trip to it.
 *
 * A farmer who travels to a mandi gets its price if it reports, and otherwise a fraction of the day's mean price at the
 * mandis that did. Weekdays on which a mandi is silent nine times in ten are treated as known closed days, so the loss is
 * the expected rupees per quintal lost to *surprise* silence on the other days. The strip shows each weekday: green is
 * reliable, red is effectively closed. A silent day may be a closed mandi or a missed upload.
 */
export default function ReportingValue() {
  const [crop, setCrop] = useState('tomato');
  const { data, isFetching } = useQuery({
    queryKey: ['mc-reporting-value', crop],
    queryFn: () => marketChoiceApi.reportingValue(crop),
    staleTime: 30 * 60 * 1000,
  });
  const rows = data?.status === 'OK' ? data.mandis ?? [] : [];
  const top = Math.max(1, ...rows.map((r) => r.expected_loss_per_q ?? 0));

  return (
    <ToolCard
      title="Silence Tax"
      subtitle="Expected rupees per quintal lost on a trip because a mandi reports no price, per mandi, from the last year of ingested prices"
      icon={<Megaphone className="h-4.5 w-4.5" />}
      accent="#f59e0b"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className={`${SELECT} capitalize`} aria-label="Crop">
          {CROPS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {data?.status === 'OK' && (
          <span className="text-xs text-neutral-signal">
            {data.window?.[0]} → {data.window?.[1]} · average loss <b className="text-foreground">{formatRupees(data.mean_expected_loss_per_q)}</b> per quintal per trip
          </span>
        )}
      </div>

      {isFetching && !data && <LoadingRow label="Reading the price history…" />}
      {data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-xs">
            <thead>
              <tr className="border-b border-border text-left text-[10px] uppercase tracking-wide text-neutral-signal">
                <th className="py-2 pr-3">Mandi</th>
                <th className="py-2 pr-3">Reported</th>
                <th className="py-2 pr-3">Surprise silence</th>
                <th className="py-2 pr-3">Week (M–S)</th>
                <th className="py-2 pr-3">Known closed</th>
                <th className="py-2 pr-3">Worst other day</th>
                <th className="py-2 text-right">Silence tax per quintal</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.mandi_id} className="border-b border-border/50">
                  <td className="py-2 pr-3 font-semibold text-foreground">{r.name}</td>
                  <td className="py-2 pr-3 font-mono tabular-nums">{Math.round(r.reported_share * 100)}%</td>
                  <td className="py-2 pr-3 font-mono tabular-nums" title="Share of its open weekdays on which it reported no price">{Math.round(r.silent_share_open_days * 100)}%</td>
                  <td className="py-2 pr-3">
                    <div className="flex gap-0.5" role="img" aria-label={`Share of days with no price, Monday to Sunday: ${r.silent_by_weekday.map((v) => Math.round(v * 100)).join(', ')} percent`}>
                      {r.silent_by_weekday.map((v, i) => (
                        <span key={i} title={`${DAYS[i]}: ${Math.round(v * 100)}% silent`} className="flex h-5 w-5 items-center justify-center rounded text-[9px] font-bold text-white" style={{ background: heat(v) }}>
                          {DAYS[i]}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2 pr-3 text-neutral-signal">{r.closed_weekdays.length ? r.closed_weekdays.join(', ') : '—'}</td>
                  <td className="py-2 pr-3 text-neutral-signal">{r.worst_open_weekday} ({Math.round(r.worst_open_weekday_silent * 100)}% silent)</td>
                  <td className="py-2">
                    <div className="flex items-center justify-end gap-2">
                      <span className="h-2 rounded-full bg-amber-500/70" style={{ width: `${Math.max(2, ((r.expected_loss_per_q ?? 0) / top) * 90)}px` }} />
                      <span className="w-20 text-right font-mono tabular-nums text-foreground">
                        {formatRupees(r.expected_loss_per_q)} <span className="text-neutral-signal">({r.expected_loss_pct ?? '—'}%)</span>
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data?.status === 'OK' && (
        <p className="mt-3 text-[11px] leading-relaxed text-neutral-signal">
          {data.note} A tax of ₹0 does not mean the mandi is reliable: it means the mandi’s usual price is below the fallback price, so silence costs no money on the price itself, but the trip is still wasted. Read it with the surprise-silence column.
        </p>
      )}
    </ToolCard>
  );
}
