'use client';

/**
 * LLM Decision Intelligence — live demo surface.
 *
 * Every other panel in this app reads pre-computed cognition state. This one
 * is different: it calls /v1/intelligence/brief, which assembles a fixed
 * evidence bundle (cognition + forecast + spillover), asks a provider to
 * reason over it, then verifies every number the provider stated actually
 * appears in that bundle before returning it. The `generated_by` and
 * `grounded` fields are shown as-is rather than summarised, because the
 * whole point of this endpoint is that the provenance is inspectable.
 */

import DeskHero from '@/components/trader/DeskHero';
import React, { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Loader2,
  Minus,
  ShieldCheck,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  WifiOff,
} from 'lucide-react';
import { mandiApi } from '@/services/api';

const COMMODITIES = [
  { id: 'tomato', label: 'Tomato' },
  { id: 'onion', label: 'Onion' },
  { id: 'potato', label: 'Potato' },
  { id: 'garlic', label: 'Garlic' },
  { id: 'ginger', label: 'Ginger' },
];

const MANDIS = [
  { id: 'kolar_apmc', label: 'Kolar APMC' },
  { id: 'bangalore_apmc', label: 'Bangalore APMC' },
];

const ACTION_STYLE: Record<string, string> = {
  BUY: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  SELL: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  WAIT: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  HOLD: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
};

const DIRECTION_ICON: Record<string, React.ReactNode> = {
  supports: <TrendingUp className="h-4 w-4 text-emerald-400 shrink-0" />,
  opposes: <TrendingDown className="h-4 w-4 text-rose-400 shrink-0" />,
  neutral: <Minus className="h-4 w-4 text-slate-500 shrink-0" />,
};

export default function AiBriefPage() {
  const [commodity, setCommodity] = useState('tomato');
  const [mandiId, setMandiId] = useState('kolar_apmc');
  const [showEvidence, setShowEvidence] = useState(false);

  const statusQuery = useQuery({
    queryKey: ['intelligence-status'],
    queryFn: () => mandiApi.getIntelligenceStatus(),
    refetchInterval: 30_000,
  });

  const briefQuery = useQuery({
    queryKey: ['intelligence-brief', commodity, mandiId, showEvidence],
    queryFn: () => mandiApi.getIntelligenceBrief(commodity, mandiId, showEvidence),
  });

  const status = statusQuery.data;
  const brief = briefQuery.data;
  const providerLabel = (status?.provider ?? '…').toUpperCase();
  const isLiveLlm = status?.provider === 'claude';

  return (
    <div className="tb-clear min-h-screen text-slate-100 font-sans antialiased">
      <div className="mx-auto max-w-4xl px-5 py-8">
        <DeskHero
          kicker="AI Brief"
          title="AI Decision Brief"
          subtitle="Reasons over the cognition, forecast and spillover evidence for one commodity at one mandi, then verifies its own output. Every number it states is checked against the evidence bundle before this page shows it to you. Nothing here is scripted."
          icon={<BrainCircuit className="h-7 w-7" />}
          accent="cyan"
          photo="desk-tomatoes"
          className="mb-7"
        >
          <div
            className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-widest ${
              isLiveLlm
                ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300'
                : 'border-slate-600 bg-slate-800/50 text-slate-300'
            }`}
            title="Which provider actually produced the last brief"
          >
            <BrainCircuit className="h-3.5 w-3.5" />
            Provider: {providerLabel}
            {status?.model_id ? ` (${status.model_id})` : ''}
          </div>
        </DeskHero>

        {/* Selectors */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <div className="flex flex-wrap gap-1.5">
            {COMMODITIES.map((c) => (
              <button
                key={c.id}
                onClick={() => setCommodity(c.id)}
                className={`rounded-lg border px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wide transition-colors ${
                  commodity === c.id
                    ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300'
                    : 'border-[#252c42] bg-[#141724] text-slate-400 hover:text-slate-200'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
          <div className="h-5 w-px bg-[#252c42]" />
          <div className="flex flex-wrap gap-1.5">
            {MANDIS.map((m) => (
              <button
                key={m.id}
                onClick={() => setMandiId(m.id)}
                className={`rounded-lg border px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wide transition-colors ${
                  mandiId === m.id
                    ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300'
                    : 'border-[#252c42] bg-[#141724] text-slate-400 hover:text-slate-200'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        {briefQuery.isLoading ? (
          <div className="flex items-center gap-3 rounded-xl border border-[#1e2335] bg-[#11131c]/80 p-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
            Generating brief for {commodity} @ {mandiId.replace('_apmc', '')}…
          </div>
        ) : briefQuery.isError ? (
          <div className="flex items-start gap-3 rounded-xl border border-rose-500/20 bg-rose-950/20 p-6 text-rose-300">
            <WifiOff className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-sm">Could not reach the intelligence service.</p>
              <p className="mt-1 text-xs text-rose-400/80">
                No evidence exists yet for this commodity/mandi pair, or the API is unreachable.
                Try a different combination, or confirm the backend is running.
              </p>
            </div>
          </div>
        ) : brief ? (
          <div className="space-y-5">
            {/* Headline card */}
            <div className="rounded-xl border border-[#1e2335] bg-[#11131c]/80 p-6">
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <span
                  className={`rounded-md border px-2.5 py-1 font-mono text-xs font-black uppercase tracking-widest ${
                    ACTION_STYLE[brief.action] || 'text-slate-300 bg-slate-800/40 border-slate-700'
                  }`}
                >
                  {brief.action}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  Confidence: <span className="text-slate-300 font-bold">{brief.confidence}</span>
                </span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  Evidence as of: <span className="text-slate-300 font-bold">{brief.evidence_as_of ?? '—'}</span>
                </span>

                <span
                  className={`ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-widest ${
                    brief.grounded
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                  }`}
                  title={
                    brief.grounded
                      ? 'Every figure in this brief was traced back to the evidence bundle.'
                      : 'One or more statements could not be traced to the evidence bundle.'
                  }
                >
                  {brief.grounded ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
                  {brief.grounded ? 'Grounded' : 'Not grounded'}
                </span>
              </div>

              <h2 className="text-lg font-bold text-white leading-snug">{brief.headline}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{brief.rationale}</p>

              {!brief.grounded && brief.grounding_issues.length > 0 && (
                <ul className="mt-3 space-y-1 rounded-lg border border-rose-500/20 bg-rose-950/10 p-3 text-xs text-rose-300">
                  {brief.grounding_issues.map((issue, i) => (
                    <li key={i}>• {issue}</li>
                  ))}
                </ul>
              )}

              <p className="mt-4 text-[11px] font-mono text-slate-600">
                generated_by: <span className="text-slate-400">{brief.generated_by}</span>
                {brief.model_id ? (
                  <>
                    {' · '}model: <span className="text-slate-400">{brief.model_id}</span>
                  </>
                ) : null}
              </p>
            </div>

            {/* Factors */}
            {brief.factors.length > 0 && (
              <div className="rounded-xl border border-[#1e2335] bg-[#11131c]/80 p-6">
                <h3 className="font-mono text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3">
                  Factors considered
                </h3>
                <div className="space-y-3">
                  {brief.factors.map((f, i) => (
                    <div key={i} className="flex items-start gap-3">
                      {DIRECTION_ICON[f.direction] ?? DIRECTION_ICON.neutral}
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-2">
                          <span className="text-sm font-bold text-slate-200">{f.label}</span>
                          <span className="font-mono text-[9px] text-slate-600">{f.evidence_ref}</span>
                        </div>
                        <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{f.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Risks + watch next */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {brief.risks.length > 0 && (
                <div className="rounded-xl border border-[#1e2335] bg-[#11131c]/80 p-5">
                  <h3 className="font-mono text-[10px] font-bold uppercase tracking-widest text-amber-400/80 mb-2.5">
                    Risks
                  </h3>
                  <ul className="space-y-1.5 text-xs leading-relaxed text-slate-400">
                    {brief.risks.map((r, i) => (
                      <li key={i}>• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.watch_next.length > 0 && (
                <div className="rounded-xl border border-[#1e2335] bg-[#11131c]/80 p-5">
                  <h3 className="font-mono text-[10px] font-bold uppercase tracking-widest text-sky-400/80 mb-2.5">
                    Watch next
                  </h3>
                  <ul className="space-y-1.5 text-xs leading-relaxed text-slate-400">
                    {brief.watch_next.map((w, i) => (
                      <li key={i}>• {w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <p className="text-[11px] leading-relaxed text-slate-600 italic">{brief.caveat}</p>

            {/* Evidence toggle */}
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="inline-flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-widest text-slate-500 hover:text-white transition-colors"
            >
              {showEvidence ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              {showEvidence ? 'Hide raw evidence bundle' : 'Show raw evidence bundle'}
            </button>

            {showEvidence && brief.evidence && (
              <pre className="max-h-96 overflow-auto rounded-xl border border-[#1e2335] bg-black/40 p-4 text-[10px] leading-relaxed text-emerald-300/90 font-mono">
                {JSON.stringify(brief.evidence, null, 2)}
              </pre>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
