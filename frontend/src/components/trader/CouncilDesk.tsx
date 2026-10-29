'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatPct } from './shared';
import { apiClient } from '@/services/api';

interface CouncilHorizon {
  agents: Record<string, number>;
  weights: Record<string, number>;
  council_pct: number;
  single_pct: number;
  council_price: number;
  promoted: boolean;
  evidence: {
    single_skill: number | null;
    council_skill: number | null;
    difference_ci: [number, number] | null;
    folds_council_beats_single: number | null;
    folds: number | null;
    agent_skill: Record<string, number>;
  };
}

interface CouncilView {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  as_of?: string;
  last_price?: number;
  agents?: string[];
  horizons?: Record<string, CouncilHorizon>;
  external_factors?: string;
}

const LABEL: Record<string, string> = {
  seasonality: 'Seasonality',
  supply: 'Supply (arrivals)',
  activity: 'Market activity',
  trend: 'Price trend',
};
const BLURB: Record<string, string> = {
  seasonality: 'Calendar position and the series’ own seasonal deviation',
  supply: 'Arrivals, their trend and the price-arrival elasticity',
  activity: 'How often the market reports and trades',
  trend: 'Price lags, returns, rolling statistics and momentum',
};

const skill = (v?: number | null) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`);

/**
 * Agent Council: four specialist forecasters (each sees one family of evidence) fused by weights learned inside each walk-forward
 * fold. The page leads with the evidence for trusting the fusion, because on this data the council is evaluated and, at every horizon
 * so far, not better than the single served model; it is shown so the specialists' views are visible, not to be traded on.
 */
export default function CouncilDesk({ commodity, mandiId }: { commodity: string; mandiId: string }) {
  const { data, isFetching } = useQuery({
    queryKey: ['council', commodity, mandiId],
    queryFn: () => apiClient<CouncilView>(`/v1/council/${commodity}/${mandiId}`),
    staleTime: 10 * 60 * 1000,
  });

  const horizons = Object.entries(data?.horizons ?? {});
  const anyPromoted = horizons.some(([, h]) => h.promoted);

  return (
    <ToolCard
      title="Agent Council"
      subtitle="Four specialist forecasters, a learned fusion, and the evidence for trusting it"
      icon={<Users className="h-4.5 w-4.5" />}
      accent="#a78bfa"
    >
      {isFetching && <LoadingRow label="Reading each agent’s forecast…" />}
      {!isFetching && data?.status === 'UNAVAILABLE' && <RefusalNotice reason={data.reason} />}

      {!isFetching && data?.status === 'OK' && (
        <div className="space-y-4">
          <div className={`rounded-xl border px-3.5 py-3 text-xs leading-relaxed ${anyPromoted ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500' : 'border-amber-500/30 bg-amber-500/10 text-amber-500'}`}>
            {anyPromoted
              ? 'The council beats the single served model at the horizons marked below, significantly and in most folds.'
              : 'At no horizon is the council significantly better than the single served model, so the served forecast stays the single model. The agents are shown so you can see which evidence pulls which way.'}
          </div>

          <p className="text-[11px] text-neutral-signal">Last price {data.last_price} on {data.as_of}. Forecast change over the horizon, by agent:</p>

          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full min-w-[560px] border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="px-3 py-2 text-left font-bold">Agent</th>
                  {horizons.map(([h]) => (
                    <th key={h} className="px-2 py-2 text-right font-bold">{h} days</th>
                  ))}
                  <th className="px-2 py-2 text-right font-bold">Skill (5d)</th>
                </tr>
              </thead>
              <tbody>
                {(data.agents ?? []).map((a) => (
                  <tr key={a} className="border-t border-border">
                    <td className="px-3 py-1.5">
                      <p className="font-semibold text-foreground">{LABEL[a] ?? a}</p>
                      <p className="text-[10px] text-neutral-signal">{BLURB[a]}</p>
                    </td>
                    {horizons.map(([h, v]) => (
                      <td key={h} className="px-2 py-1.5 text-right font-mono text-foreground">
                        {formatPct(v.agents[a], 2)}
                        <span className="block text-[10px] text-neutral-signal">weight {v.weights[a].toFixed(2)}</span>
                      </td>
                    ))}
                    <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{skill(data.horizons?.['5']?.evidence.agent_skill[a])}</td>
                  </tr>
                ))}
                <tr className="border-t-2 border-border bg-surface-2/60">
                  <td className="px-3 py-1.5 font-bold text-foreground">Council (fused)</td>
                  {horizons.map(([h, v]) => (
                    <td key={h} className="px-2 py-1.5 text-right font-mono font-bold text-foreground">{formatPct(v.council_pct, 2)}</td>
                  ))}
                  <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{skill(data.horizons?.['5']?.evidence.council_skill)}</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-3 py-1.5 font-bold text-foreground">Single served model</td>
                  {horizons.map(([h, v]) => (
                    <td key={h} className="px-2 py-1.5 text-right font-mono font-bold text-foreground">{formatPct(v.single_pct, 2)}</td>
                  ))}
                  <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{skill(data.horizons?.['5']?.evidence.single_skill)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full min-w-[480px] border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
                  <th className="px-3 py-2 text-left font-bold">Horizon</th>
                  <th className="px-2 py-2 text-right font-bold">Council − single (abs. error, 95% CI)</th>
                  <th className="px-2 py-2 text-right font-bold">Folds won</th>
                  <th className="px-2 py-2 text-left font-bold">Trusted over single?</th>
                </tr>
              </thead>
              <tbody>
                {horizons.map(([h, v]) => (
                  <tr key={h} className="border-t border-border">
                    <td className="px-3 py-1.5 font-semibold text-foreground">{h} days</td>
                    <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">
                      {v.evidence.difference_ci ? `[${v.evidence.difference_ci[0].toFixed(5)}, ${v.evidence.difference_ci[1].toFixed(5)}]` : '—'}
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{v.evidence.folds_council_beats_single}/{v.evidence.folds}</td>
                    <td className="px-2 py-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${v.promoted ? 'bg-emerald-500/15 text-emerald-500' : 'bg-neutral-500/10 text-neutral-signal'}`}>
                        {v.promoted ? 'yes' : 'no'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-[11px] leading-relaxed text-neutral-signal">
            Skill is the reduction in mean absolute error against “no change”, on held-out walk-forward folds. A difference interval containing 0 means the
            two cannot be told apart. Weights are learned inside each fold from the agents’ out-of-sample predictions and sum to at most 1, so the council can
            average or shrink the agents but not amplify them. {data.external_factors ? `External factors (weather, news): ${data.external_factors}.` : ''}
          </p>
        </div>
      )}
    </ToolCard>
  );
}
