'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Archive,
  BarChart3,
  BrainCircuit,
  ChevronRight,
  Command,
  Database,
  Gauge,
  Layers3,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Signal,
  Sparkles,
  Zap,
} from 'lucide-react';
import { useCognitionStream } from '@/hooks/useCognitionStream';

type ViewMode = 'INTELLIGENCE' | 'QUERY' | 'EVENTS';

type Directive = {
  primary_directive?: string;
  action_code?: string;
  urgency?: string;
  reasoning?: string;
};

type Agent = {
  agent_id?: string;
  signal?: string;
  confidence?: number;
  weight?: number;
};

type MarketState = {
  commodity?: string;
  mandi_id?: string;
  directives?: Directive | Directive[] | string;
  confidence?: { score?: number };
  deliberation?: { agents?: Agent[]; chaos_score?: number };
  price_prediction?: number;
  trend?: string;
  risk_level?: string;
  regime?: string;
  volatility?: { regime?: string };
  integrity_status?: string;
  forecast_arrivals?: number;
};

type CognitionEvent = {
  id: string | number;
  timestamp: string;
  message: string;
  type: string;
};

type AuditEntry = {
  id?: string | number;
  action?: string;
  actor?: string;
  timestamp?: string;
  details?: string;
};

type MemoryEntry = {
  id?: string | number;
  type?: string;
  commodity?: string;
  timestamp: string;
};

type SystemHealth = {
  services?: Record<string, string | boolean | number | object>;
  cognition_reliability?: {
    cycle_count?: number;
    avg_cycle_duration_sec?: number;
    uptime_sec?: number;
  };
};

type QuickHealth = {
  intelligence_available?: boolean;
  commodities_with_intelligence?: string[];
};

type QueryResult = {
  decision?: string;
  summary?: string;
  reasoning?: string;
  market_insight?: string;
};

const getDirective = (directives?: Directive | Directive[] | string): Directive | undefined => {
  const directive = Array.isArray(directives) ? directives[0] : directives;
  if (typeof directive === 'string') {
    return {
      primary_directive: directive,
      reasoning: directive,
      action_code: 'EXECUTE',
    };
  }
  return directive;
};

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const formatTime = (value?: string | number | Date | null) => {
  if (!value) return '';
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value;
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(date);
};

const formatDate = (value?: string | number | Date | null) => {
  if (!value) return '';
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  }).format(date);
};

const actionTone = (value = '') => {
  const upper = value.toUpperCase();
  if (upper.includes('SELL')) return 'risk';
  if (upper.includes('BUY') || upper.includes('ACCUMULATE')) return 'positive';
  if (upper.includes('HOLD')) return 'stable';
  if (upper.includes('WAIT')) return 'warning';
  return 'neutral';
};

const toneClass: Record<string, string> = {
  positive: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10',
  stable: 'text-sky-300 border-sky-400/25 bg-sky-400/8',
  warning: 'text-amber-300 border-amber-300/30 bg-amber-300/10',
  risk: 'text-rose-300 border-rose-400/30 bg-rose-400/12',
  neutral: 'text-slate-300 border-slate-700/50 bg-slate-950/70',
};

const getOpportunityScore = (state: MarketState) => {
  return Math.max(0, Math.min(1, state.confidence?.score ?? 0));
};

const selectStrongestOpportunity = (states: MarketState[]) => {
  if (!states || states.length === 0) return null;
  return [...states].sort((a, b) => getOpportunityScore(b) - getOpportunityScore(a))[0] ?? null;
};

const formatTrend = (trend?: string) => {
  if (!trend) return 'No trend available';
  return trend.replace(/_/g, ' ').toUpperCase();
};

const marketChangeSummary = (state: MarketState) => {
  if (state.trend) return `${formatTrend(state.trend)} movement detected`;
  if (state.regime) return `${state.regime.replace(/_/g, ' ').toUpperCase()} regime`;
  return 'Market movement equilibrium';
};

function StatusDot({ ok, pulse = false }: { ok: boolean; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2.5 w-2.5 items-center justify-center">
      {ok && pulse && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[rgba(52,211,153,0.25)] opacity-90" />}
      <span className={cx('relative h-1.5 w-1.5 rounded-full', ok ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.6)] animate-pulse' : 'bg-rose-400')} />
    </span>
  );
}

const IndiaMapIcon = () => (
  <svg className="absolute right-2 bottom-2 w-14 h-14 opacity-25 text-emerald-400 pointer-events-none select-none" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="15" r="1.5" fill="currentColor" />
    <circle cx="45" cy="25" r="1.5" fill="currentColor" />
    <circle cx="55" cy="30" r="1.5" fill="currentColor" />
    <circle cx="35" cy="40" r="1.5" fill="currentColor" />
    <circle cx="65" cy="42" r="1.5" fill="currentColor" />
    <circle cx="40" cy="50" r="1.5" fill="currentColor" />
    <circle cx="58" cy="52" r="1.5" fill="currentColor" />
    <circle cx="45" cy="65" r="1.5" fill="currentColor" />
    <circle cx="52" cy="78" r="1.5" fill="currentColor" />
    <circle cx="50" cy="90" r="2" fill="currentColor" className="animate-ping" />
    
    <path d="M50 15 L45 25 L35 40 L40 50 L45 65 L52 78 L50 90" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2,2" />
    <path d="M50 15 L55 30 L65 42 L58 52 L45 65" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2,2" />
    <path d="M45 25 L55 30 M35 40 L58 52 M40 50 L58 52" stroke="currentColor" strokeWidth="0.5" strokeDasharray="1,2" />
  </svg>
);

const RadarIcon = () => (
  <svg className="absolute right-2 bottom-2 w-12 h-12 opacity-30 text-emerald-400 pointer-events-none select-none" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2,2" />
    <circle cx="50" cy="50" r="30" stroke="currentColor" strokeWidth="0.5" />
    <circle cx="50" cy="50" r="15" stroke="currentColor" strokeWidth="0.5" />
    <circle cx="50" cy="50" r="2" fill="currentColor" />
    
    <line x1="50" y1="50" x2="80" y2="20" stroke="currentColor" strokeWidth="1" className="origin-center" style={{ transformOrigin: '50px 50px', animation: 'spin 4s linear infinite' }} />
    <style>{`
      @keyframes spin {
        100% { transform: rotate(360deg); }
      }
    `}</style>
  </svg>
);

const RingProgressIcon = () => (
  <svg className="absolute right-2 bottom-2 w-12 h-12 text-emerald-400 opacity-60 pointer-events-none select-none" viewBox="0 0 36 36">
    <path
      className="text-zinc-800"
      strokeWidth="2.5"
      stroke="currentColor"
      fill="none"
      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
    />
    <path
      className="text-emerald-400 animate-pulse"
      strokeWidth="2.5"
      strokeDasharray="65, 100"
      strokeLinecap="round"
      stroke="currentColor"
      fill="none"
      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
    />
  </svg>
);

const LatencyWaveIcon = () => (
  <svg className="absolute right-2 bottom-2 w-14 h-8 text-fuchsia-400 opacity-60 pointer-events-none select-none" viewBox="0 0 100 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M0 20 Q10 5, 20 20 T40 20 T60 20 T80 20 T100 20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="stroke-linejoin-round" />
    <path d="M0 20 Q10 5, 20 20 T40 20 T60 20 T80 20 T100 20" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="stroke-linejoin-round blur-[2px] opacity-40" />
  </svg>
);

const WorldMapIllustration = () => (
  <div className="world-map-container pointer-events-none select-none">
    <svg viewBox="0 0 1000 500" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M150,150 A20,20 0 0,1 250,160 M300,120 A40,40 0 0,1 400,180 M450,220 A10,10 0 0,0 480,240 M520,100 A15,15 0 0,1 600,120 M700,130 A30,30 0 0,1 800,220 M850,180 A10,10 0 0,1 920,240" stroke="currentColor" strokeWidth="2" strokeDasharray="5,15" className="text-emerald-400" />
      <path d="M180,250 A50,50 0 0,0 280,350 M320,380 A30,30 0 0,0 350,420 M550,250 A80,80 0 0,1 650,400 M750,280 A40,40 0 0,1 850,380" stroke="currentColor" strokeWidth="2" strokeDasharray="5,15" className="text-emerald-400" />
      
      <circle cx="620" cy="240" r="8" fill="#34d399" className="animate-pulse" />
      <circle cx="620" cy="240" r="16" stroke="#34d399" strokeWidth="1" strokeDasharray="2,2" />
      
      <path d="M620,240 Q400,150 220,160" stroke="#34d399" strokeWidth="0.5" strokeDasharray="4,4" />
      <path d="M620,240 Q750,150 880,180" stroke="#34d399" strokeWidth="0.5" strokeDasharray="4,4" />
      <path d="M620,240 Q500,320 300,350" stroke="#22d3ee" strokeWidth="0.5" strokeDasharray="4,4" />
      <path d="M620,240 Q700,350 800,330" stroke="#22d3ee" strokeWidth="0.5" strokeDasharray="4,4" />
    </svg>
  </div>
);

function Sparkline({ type = 'up', tone = 'stable' }: { type?: string; tone?: string }) {
  const color = tone === 'risk' ? '#fb7185' : tone === 'positive' ? '#34d399' : tone === 'warning' ? '#fbbf24' : '#22d3ee';
  
  let points = "0,15 15,10 30,18 45,5 60,12 75,3 90,8";
  if (type === 'down') {
    points = "0,3 15,12 30,5 45,15 60,8 75,18 90,14";
  } else if (type === 'stable') {
    points = "0,10 15,10 30,12 45,9 60,10 75,10 90,11";
  } else if (type === 'chaos') {
    points = "0,18 15,4 30,15 45,6 60,17 75,3 90,16";
  }
  
  return (
    <div className="mt-2 h-6 w-full opacity-65">
      <svg className="w-full h-full" viewBox="0 0 90 20" preserveAspectRatio="none">
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          points={points}
          className="stroke-linecap-round stroke-linejoin-round"
        />
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="3"
          points={points}
          className="stroke-linecap-round stroke-linejoin-round blur-[2px] opacity-40"
        />
      </svg>
    </div>
  );
}

function StatusBadge({
  label,
  variant = 'stable',
  pulse = false,
}: {
  label: string;
  variant?: 'open' | 'active' | 'stable' | 'warning' | 'critical';
  pulse?: boolean;
}) {
  return (
    <span className={cx('status-pill', `status-${variant}`, pulse && 'animate-pulse/60')}>{label}</span>
  );
}

function Button({
  children,
  icon: Icon,
  variant = 'secondary',
  active = false,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: React.ElementType;
  variant?: 'primary' | 'secondary' | 'tertiary';
  active?: boolean;
}) {
  return (
    <button
      {...props}
      className={cx(
        'group inline-flex items-center justify-center gap-2 border font-mono text-[10px] font-semibold uppercase tracking-[0.18em] transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(72,208,255,0.5)] focus-visible:ring-offset-2 focus-visible:ring-offset-[rgba(4,7,12,1)]',
        'disabled:pointer-events-none disabled:opacity-45',
        variant === 'primary' &&
          'h-9 border-[rgba(72,208,255,0.35)] bg-[rgba(72,208,255,0.14)] px-4 text-[var(--accent)] shadow-[0_10px_28px_-20px_rgba(72,208,255,0.8)] hover:-translate-y-px hover:border-[rgba(94,231,255,0.45)] hover:bg-[rgba(94,231,255,0.16)]',
        variant === 'secondary' &&
          'h-8 border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,38,0.92)] px-3 text-slate-300 hover:-translate-y-px hover:border-[rgba(72,208,255,0.2)] hover:bg-[rgba(72,208,255,0.08)] hover:text-slate-100',
        variant === 'tertiary' &&
          'h-7 border-transparent bg-transparent px-2 text-slate-500 hover:bg-[rgba(148,163,184,0.1)] hover:text-slate-100',
        active && 'border-[rgba(94,231,255,0.5)] bg-[rgba(72,208,255,0.16)] text-[var(--accent)] shadow-[0_0_28px_-12px_rgba(72,208,255,0.35)]',
        className,
      )}
    >
      {Icon && <Icon className="h-3.5 w-3.5 transition-transform duration-200 group-hover:scale-110" />}
      {children}
    </button>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  meta,
  tier = 'T3',
}: {
  icon: React.ElementType;
  title: string;
  meta?: string;
  tier?: string;
}) {
  let headerClass = 'section-header-viewport';
  if (tier === 'T3') {
    headerClass = 'section-header-archive';
  } else if (tier === 'T2') {
    headerClass = 'section-header-recovery';
  }
  
  return (
    <div className={cx("surface-panel flex h-11 items-center justify-between border-b border-white/5 px-4", headerClass)}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[var(--accent)]" />
        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-slate-200">{title}</span>
      </div>
      <div className="flex items-center gap-2">
        {meta && <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-500">{meta}</span>}
        <span className="rounded-sm border border-slate-800 bg-slate-950/80 px-2 py-1 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-500">{tier}</span>
      </div>
    </div>
  );
}

function MetricTile({ label, value, sub, tone = 'neutral' }: { label: string; value: React.ReactNode; sub?: string; tone?: string }) {
  const isForecast = label.toUpperCase().includes('FORECAST') || label.toUpperCase().includes('PRICE');
  const isRisk = label.toUpperCase().includes('RISK');
  const isVolatility = label.toUpperCase().includes('VOLATILITY');
  const isChaos = label.toUpperCase().includes('CHAOS');
  
  let sparkType = 'stable';
  if (isForecast) sparkType = 'up';
  if (isRisk) sparkType = 'down';
  if (isVolatility) sparkType = 'stable';
  if (isChaos) sparkType = 'chaos';

  return (
    <div className={cx('metric-tile-premium surface-card border p-4 relative overflow-hidden flex flex-col justify-between min-h-[95px] transition-all duration-300 hover:scale-[1.02]', toneClass[tone])}>
      <div>
        <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">{label}</div>
        <div className="font-mono text-xl font-black tracking-tight text-slate-100">{value}</div>
      </div>
      <div className="flex items-end justify-between mt-2 gap-2">
        {sub && <span className="truncate font-mono text-[8px] uppercase tracking-[0.12em] text-slate-500">{sub}</span>}
        <div className="w-20 h-6 shrink-0">
          <Sparkline type={sparkType} tone={tone} />
        </div>
      </div>
    </div>
  );
}

function ConfidenceBar({ value, tone = 'stable' }: { value: number; tone?: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = tone === 'risk' ? 'from-rose-500 to-amber-300' : tone === 'positive' ? 'from-emerald-400 to-cyan-300' : 'from-cyan-400 to-blue-300';
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.18em]">
        <span className="text-zinc-500">Trust Vector</span>
        <span className="text-zinc-200">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden border border-zinc-800 bg-zinc-950">
        <div className={cx('h-full bg-gradient-to-r transition-all duration-500 confidence-bar-fill', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function PrimaryRegime({ state }: { state: MarketState }) {
  const directive = getDirective(state.directives);
  const action = directive?.primary_directive ?? directive?.action_code ?? 'SYNTHESIZING';
  const tone = actionTone(action);
  const confidence = state.confidence?.score ?? 0;
  const trend = state.trend ? formatTrend(state.trend) : 'UNKNOWN';
  const risk = state.risk_level ?? 'UNKNOWN';
  const changeSummary = marketChangeSummary(state);
  const summary = directive?.reasoning || `${state.commodity?.toUpperCase() ?? 'COMMODITY'} is moving into a ${trend.toLowerCase()} regime.`;
  const avoid = risk === 'HIGH' ? 'Avoid adding size until signs of reversal clear.' : 'Avoid chasing the move without a clarity signal.';

  return (
    <section className="overflow-hidden border border-cyan-300/20 bg-[linear-gradient(135deg,rgba(3,12,23,0.85),rgba(4,10,25,0.95))] shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_20px_80px_rgba(0,0,0,0.35)]">
      <div className="p-5">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">Command Signal</div>
            <h2 className="mt-2 text-3xl font-black tracking-tight text-zinc-100">{action.toUpperCase()} {state.commodity?.toUpperCase() ?? 'MARKET'}</h2>
            <div className="mt-3 max-w-2xl text-sm leading-6 text-zinc-300">{summary}</div>
          </div>
          <div className={cx('rounded-2xl border px-4 py-3 text-right', toneClass[tone])}>
            <div className="font-mono text-[8px] uppercase tracking-[0.24em] opacity-75">Confidence</div>
            <div className="mt-1 text-3xl font-black">{(confidence * 100).toFixed(0)}%</div>
            <div className="mt-1 text-[10px] uppercase tracking-[0.22em] text-zinc-300">{risk === 'HIGH' ? 'High risk' : 'Operational risk'}</div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded border border-zinc-900 bg-zinc-950/70 p-4">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">Action</div>
            <div className="mt-2 text-xl font-black text-zinc-100">{action.toUpperCase()}</div>
          </div>
          <div className="rounded border border-zinc-900 bg-zinc-950/70 p-4">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">Signal</div>
            <div className="mt-2 text-xl font-black text-zinc-100">{trend}</div>
          </div>
          <div className="rounded border border-zinc-900 bg-zinc-950/70 p-4">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">Opportunity</div>
            <div className="mt-2 text-xl font-black text-zinc-100">{changeSummary}</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="rounded border border-zinc-900 bg-black/40 p-4">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">Why now?</div>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{summary}</p>
          </div>
          <div className="rounded border border-zinc-900 bg-black/40 p-4">
            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">Avoid</div>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{avoid}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function OpportunityLeaderboard({ states, activeIdx, onSelect }: { states: MarketState[]; activeIdx: number; onSelect: (index: number) => void }) {
  const sorted = [...states].sort((a, b) => getOpportunityScore(b) - getOpportunityScore(a));

  return (
    <section className="surface-card border border-white/5 p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-400">Opportunity Leaderboard</div>
          <div className="mt-1 text-sm text-zinc-300">Best active trades ranked by system confidence.</div>
        </div>
        <div className="rounded-full border border-zinc-800 bg-zinc-950/70 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-500">{sorted.length} markets</div>
      </div>
      <div className="space-y-3">
        {sorted.slice(0, 5).map((state, index) => {
          const directive = getDirective(state.directives);
          const action = directive?.primary_directive ?? directive?.action_code ?? 'SYNTHESIZING';
          const confidence = state.confidence?.score ?? 0;
          const risk = state.risk_level ?? 'UNKNOWN';
          const selected = index === activeIdx;
          return (
            <button
              key={`${state.commodity}-${state.mandi_id}-${index}`}
              onClick={() => onSelect(index)}
              className={cx(
                'group w-full rounded border px-4 py-3 text-left transition-all duration-200',
                selected ? 'border-cyan-300/50 bg-cyan-400/[0.06]' : 'border-zinc-900 bg-zinc-950/60 hover:border-zinc-700 hover:bg-zinc-900/70',
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-400">{state.commodity}</div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-200">{state.mandi_id?.replace(/_/g, ' ')}</div>
                </div>
                <span className={cx('rounded-full px-2 py-1 text-[9px] uppercase tracking-[0.15em]', state.risk_level === 'HIGH' ? 'bg-rose-500/10 text-rose-300 border border-rose-400/20' : 'bg-emerald-500/10 text-emerald-300 border border-emerald-400/20')}>{risk}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
                <span>{action}</span>
                <span>{(confidence * 100).toFixed(0)}%</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function MarketNarrative({ state }: { state: MarketState }) {
  const directive = getDirective(state.directives);
  const trend = state.trend ? formatTrend(state.trend) : 'unknown';
  return (
    <section className="surface-card border border-white/5 p-4">
      <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-400">Market Narrative</div>
      <div className="mt-3 text-sm leading-6 text-zinc-200">
        {directive?.reasoning || `The system sees ${state.commodity?.toLowerCase()} moving into a ${trend} regime with ${state.risk_level?.toLowerCase() ?? 'unknown'} risk.`}
      </div>
      <div className="mt-3 space-y-2 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
        {state.regime && <div>Regime: {state.regime.replace(/_/g, ' ')}</div>}
        {state.volatility?.regime && <div>Volatility: {state.volatility.regime}</div>}
        {state.forecast_arrivals !== undefined && <div>Arrival forecast: {state.forecast_arrivals}</div>}
      </div>
    </section>
  );
}

function ConsensusRadar({ state }: { state: MarketState }) {
  const agents = Array.isArray(state.deliberation?.agents) ? state.deliberation.agents : [];
  return (
    <section className="surface-card border border-white/5 p-4">
      <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-400">Consensus Radar</div>
      <div className="mt-4 space-y-2">
        {agents.length === 0 ? (
          <div className="rounded border border-zinc-900 bg-zinc-950/60 p-4 text-sm text-zinc-500">Consensus data is still aggregating.</div>
        ) : (
          agents.slice(0, 6).map((agent, index) => {
            const confidence = Math.max(0, Math.min(100, (agent.confidence ?? agent.weight ?? 0.5) * 100));
            return (
              <div key={`${agent.agent_id}-${index}`} className="space-y-1 rounded border border-zinc-900 bg-zinc-950/60 p-3">
                <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.16em] text-zinc-400">
                  <span>{agent.agent_id}</span>
                  <span>{confidence.toFixed(0)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full border border-zinc-800 bg-black">
                  <div className="h-full bg-cyan-400" style={{ width: `${confidence}%` }} />
                </div>
                <div className="text-[9px] uppercase tracking-[0.14em] text-zinc-500">{agent.signal || 'signal unavailable'}</div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

function WhatChanged({ state, events, latestUpdate }: { state: MarketState; events: CognitionEvent[]; latestUpdate: any }) {
  const latestEvent = events[0];
  return (
    <section className="surface-card border border-white/5 p-4">
      <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-400">What Changed</div>
      <div className="mt-3 text-sm leading-6 text-zinc-200">{marketChangeSummary(state)} since the last intelligence update.</div>
      <div className="mt-4 space-y-2 rounded border border-zinc-900 bg-zinc-950/60 p-3 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
        <div>Last sync: {latestUpdate ? formatTime((latestUpdate as any).timestamp || new Date()) : 'waiting for event'}</div>
        {latestEvent && <div>Latest event: {latestEvent.message}</div>}
      </div>
    </section>
  );
}

function MarketPulse({ allStates, quickHealth, status, latestUpdate }: { allStates: MarketState[]; quickHealth: QuickHealth | null; status: string; latestUpdate: any }) {
  return (
    <section className="grid gap-3 md:grid-cols-3">
      <MetricTile label="Active Opportunities" value={allStates.length} sub="markets" tone="stable" />
      <MetricTile label="Intelligence" value={quickHealth?.intelligence_available ? 'READY' : 'PENDING'} sub="data readiness" tone={quickHealth?.intelligence_available ? 'positive' : 'warning'} />
      <MetricTile label="Stream Status" value={status} sub={latestUpdate ? formatTime((latestUpdate as any).timestamp || new Date()) : 'waiting'} tone={status === 'LIVE' ? 'stable' : 'risk'} />
    </section>
  );
}

function MarketCard({ state, active, onClick }: { state: MarketState; active: boolean; onClick: () => void }) {
  const directive = getDirective(state.directives);
  const action = directive?.primary_directive ?? 'SYNTHESIZING';
  const tone = actionTone(action);
  const confidence = state.confidence?.score ?? 0;

  return (
    <button
      onClick={onClick}
      className={cx(
        'group border bg-zinc-950/55 p-3 text-left transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-offset-2 focus-visible:ring-offset-black',
        active ? 'border-cyan-300/50 bg-cyan-400/[0.06] shadow-[0_0_28px_rgba(34,211,238,0.12)]' : 'border-zinc-900 hover:-translate-y-px hover:border-zinc-700 hover:bg-zinc-900/70',
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[9px] font-bold uppercase tracking-[0.2em] text-zinc-500">{state.commodity}</div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-600">{state.mandi_id?.replace('_apmc', '')}</div>
        </div>
        <ChevronRight className={cx('h-3.5 w-3.5 transition-transform duration-200', active ? 'text-cyan-300' : 'text-zinc-700 group-hover:translate-x-0.5 group-hover:text-zinc-400')} />
      </div>
      <div className={cx('mb-2 inline-flex max-w-full border px-2 py-1 font-mono text-[10px] font-black uppercase tracking-[0.12em]', toneClass[tone])}>
        <span className="truncate">{action}</span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-zinc-600">Price</div>
          <div className="font-mono text-sm font-black text-zinc-200">Rs {(state.price_prediction ?? 0).toFixed(0)}</div>
        </div>
        <div className="min-w-20">
          <div className="mb-1 text-right font-mono text-[9px] text-zinc-500">{(confidence * 100).toFixed(0)}%</div>
          <div className="h-1.5 border border-zinc-800 bg-black">
            <div className="h-full bg-cyan-300" style={{ width: `${Math.max(0, Math.min(100, confidence * 100))}%` }} />
          </div>
        </div>
      </div>
    </button>
  );
}

function EventFeed({ events, large = false }: { events: CognitionEvent[]; large?: boolean }) {
  const colors: Record<string, string> = {
    success: 'border-cyan-300/35 text-cyan-200',
    error: 'border-rose-400/40 text-rose-200',
    warning: 'border-amber-300/40 text-amber-200',
    system: 'border-zinc-700 text-zinc-400',
    update: 'border-emerald-400/35 text-emerald-200',
    query: 'border-violet-400/35 text-violet-200',
    simulation: 'border-fuchsia-400/35 text-fuchsia-200',
    info: 'border-zinc-800 text-zinc-500',
  };

  if (events.length === 0) {
    return <div className="border border-dashed border-zinc-900 p-6 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-700">Waiting for cognition events</div>;
  }

  return (
    <div className={cx('space-y-1.5', large && 'space-y-2')}>
      {events.map((event) => (
        <div
          key={event.id}
          className={cx(
            'animate-[eventIn_220ms_ease-out] border-l-2 bg-zinc-950/40 px-3 py-2 transition-all duration-200 hover:bg-zinc-900/55',
            colors[event.type] ?? colors.info,
          )}
        >
          <div className="flex items-start gap-3">
            <span className="w-16 shrink-0 font-mono text-[9px] uppercase tracking-[0.12em] text-zinc-700">{formatTime(event.timestamp)}</span>
            <span className={cx('font-mono leading-5', large ? 'text-[11px]' : 'text-[10px]')}>{event.message}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function QueryConsole({ onSubmit, result, isQuerying }: { onSubmit: (q: string) => void; result: QueryResult | null; isQuerying: boolean }) {
  const [query, setQuery] = useState('');
  const examples = ['Should I sell tomatoes today?', 'What commodity is strongest?', 'Which mandi has highest upside?', 'Is onion market safe to enter?'];
  const decisionTone = actionTone(result?.decision ?? '');

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim() && !isQuerying) onSubmit(query.trim());
  };

  return (
    <div className="space-y-4">
      <form onSubmit={submit} className="flex gap-2 border border-cyan-300/20 bg-zinc-950/75 p-2 shadow-[0_0_34px_rgba(34,211,238,0.08)]">
        <div className="flex flex-1 items-center gap-3 border border-zinc-900 bg-black px-3">
          <Search className="h-4 w-4 text-cyan-300/70" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask TraderOS about sell timing, risk, strength, or mandi advantage"
            className="h-11 flex-1 bg-transparent font-mono text-sm text-zinc-100 placeholder:text-zinc-700 focus:outline-none"
          />
        </div>
        <Button type="submit" disabled={isQuerying} variant="primary" icon={Command} className="h-auto">
          {isQuerying ? 'Resolving' : 'Query'}
        </Button>
      </form>

      <div className="grid gap-2 md:grid-cols-2">
        {examples.map((example) => (
          <button
            key={example}
            onClick={() => onSubmit(example)}
            className="group flex items-center justify-between border border-zinc-900 bg-zinc-950/45 px-3 py-2 text-left font-mono text-[11px] text-zinc-500 transition-all duration-200 hover:border-cyan-400/25 hover:bg-cyan-400/[0.04] hover:text-zinc-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70"
          >
            <span>{example}</span>
            <ChevronRight className="h-3.5 w-3.5 text-zinc-700 transition-transform group-hover:translate-x-0.5 group-hover:text-cyan-300" />
          </button>
        ))}
      </div>

      {result && (
        <div className={cx('border p-5', toneClass[decisionTone])}>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] opacity-70">Query Decision</div>
              <div className="mt-1 text-5xl font-black tracking-tight">{result.decision}</div>
            </div>
            <Sparkles className="h-5 w-5 opacity-70" />
          </div>
          <p className="max-w-3xl text-xl font-bold leading-7 text-zinc-100">{result.summary}</p>
          <p className="mt-4 border-l border-current/40 pl-4 text-sm leading-6 text-zinc-300">{result.reasoning}</p>
          {result.market_insight && <p className="mt-4 font-mono text-[11px] leading-5 text-zinc-500">{result.market_insight}</p>}
        </div>
      )}
    </div>
  );
}
function AuditPanel({ auditLog, memories }: { auditLog: AuditEntry[]; memories: MemoryEntry[] }) {
  if (auditLog.length === 0 && memories.length === 0) {
    return (
      <div className="p-4">
        <div className="border border-dashed border-zinc-900 p-5 text-center">
          <Archive className="mx-auto mb-3 h-5 w-5 text-zinc-700" />
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-600">No audit records yet</div>
          <p className="mt-2 text-xs leading-5 text-zinc-700">Records appear after cognition generates or refreshes.</p>
        </div>
      </div>
    );
  }

  const getAuditStyle = (action = '', details = '') => {
    const act = action.toUpperCase();
    const det = details.toUpperCase();
    if (act.includes('GINGER') || det.includes('GINGER')) return { color: 'border-emerald-500 text-emerald-400 bg-emerald-950/40', glow: 'shadow-[0_0_15px_rgba(52,211,153,0.3)]' };
    if (act.includes('ONION') || det.includes('ONION')) return { color: 'border-fuchsia-500 text-fuchsia-400 bg-fuchsia-950/40', glow: 'shadow-[0_0_15px_rgba(232,121,249,0.3)]' };
    if (act.includes('GARLIC') || det.includes('GARLIC')) return { color: 'border-amber-500 text-amber-400 bg-amber-950/40', glow: 'shadow-[0_0_15px_rgba(251,191,36,0.3)]' };
    if (act.includes('TOMATO') || det.includes('TOMATO')) return { color: 'border-cyan-500 text-cyan-400 bg-cyan-950/40', glow: 'shadow-[0_0_15px_rgba(34,211,238,0.3)]' };
    return { color: 'border-slate-500 text-slate-400 bg-slate-900/40', glow: 'shadow-[0_0_15px_rgba(148,163,184,0.2)]' };
  };

  return (
    <div className="relative p-3 space-y-4">
      <div className="relative space-y-3">
        {auditLog.slice(0, 10).map((entry, index) => {
          const style = getAuditStyle(entry.action, entry.details);
          return (
            <div key={entry.id ?? index} className="flex gap-3 items-start border border-white/5 bg-zinc-950/50 p-3 hover:border-emerald-500/20 hover:bg-zinc-900/40 transition-all duration-200">
              <div className={cx("w-8 h-8 rounded border flex items-center justify-center shrink-0", style.color, style.glow)}>
                <BrainCircuit className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center">
                  <span className="font-mono text-[9px] font-black uppercase tracking-[0.15em] text-zinc-300">{entry.action ?? 'SYNTHESIZE_PLAN'}</span>
                  <span className="font-mono text-[8px] text-zinc-500">{entry.timestamp ? formatTime(entry.timestamp) : ''}</span>
                </div>
                <div className="font-mono text-[8px] font-bold uppercase tracking-[0.2em] text-emerald-400/80 mt-0.5">{entry.actor ?? 'SYSTEM'}</div>
                <p className="text-[10px] text-zinc-400 leading-normal mt-1">{entry.details}</p>
              </div>
            </div>
          );
        })}
        
        {memories.slice(0, 4).map((memory, index) => (
          <div key={memory.id ?? index} className="flex gap-3 items-start border border-white/5 bg-black/40 p-3">
            <div className="w-8 h-8 rounded border border-violet-500/30 text-violet-400 bg-violet-950/20 flex items-center justify-center shrink-0">
              <Database className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-violet-300">{memory.type} / {memory.commodity}</div>
              <div className="mt-1 font-mono text-[8px] text-zinc-600">{formatDate(memory.timestamp)}</div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="pointer-events-none absolute bottom-0 left-0 w-36 h-36 opacity-20 filter blur-[30px] bg-emerald-500/20 rounded-full -ml-16 -mb-16 z-0" />
    </div>
  );
}

function HealthPanel({
  systemHealth,
  allStates,
  quickHealth,
  cognitionEvents,
  latestUpdate,
}: {
  systemHealth: SystemHealth | null;
  allStates: MarketState[];
  quickHealth: QuickHealth | null;
  cognitionEvents: CognitionEvent[];
  latestUpdate: any;
}) {
  const services = systemHealth?.services ?? {};
  const reliability = systemHealth?.cognition_reliability ?? {};
  const serviceEntries = Object.entries(services);

  return (
    <div className="space-y-4 p-4 relative overflow-hidden">
      <div className="grid gap-2">
        {serviceEntries.length === 0 ? (
          <div className="border border-zinc-900 p-3 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-700">Fetching infrastructure state</div>
        ) : (
          serviceEntries.map(([key, value]) => (
            <div key={key} className="flex items-center justify-between border border-white/5 bg-zinc-950/45 px-3 py-2 hover:bg-zinc-900/30 transition-all duration-200">
              <div className="flex items-center gap-2">
                <StatusDot ok={value === 'OPEN' || value === 'alive' || value === 'ok'} pulse />
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-300">{key}</span>
              </div>
              <span className="font-mono text-[9px] font-bold uppercase tracking-[0.14em] text-emerald-400">
                {typeof value === 'string' ? value.toUpperCase() : value ? 'ALIVE +' : 'OFFLINE'}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="surface-card border border-white/5 p-4 relative overflow-hidden bg-zinc-950/45 min-h-[95px] flex flex-col justify-between transition-all duration-300 hover:scale-[1.02]">
          <div>
            <div className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Markets Covered</div>
            <div className="font-mono text-xl font-black text-slate-100 mt-1">{allStates.length}</div>
            <div className="font-mono text-[8px] uppercase tracking-[0.12em] text-cyan-400 mt-0.5">Live contexts</div>
          </div>
          <IndiaMapIcon />
        </div>

        <div className="surface-card border border-white/5 p-4 relative overflow-hidden bg-zinc-950/45 min-h-[95px] flex flex-col justify-between transition-all duration-300 hover:scale-[1.02]">
          <div>
            <div className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Intelligence</div>
            <div className="font-mono text-xl font-black text-slate-100 mt-1">{quickHealth?.intelligence_available ? 'ACTIVE' : 'PENDING'}</div>
            <div className="font-mono text-[8px] uppercase tracking-[0.12em] text-emerald-400 mt-0.5">Availability</div>
          </div>
          <RadarIcon />
        </div>

        <div className="surface-card border border-white/5 p-4 relative overflow-hidden bg-zinc-950/45 min-h-[95px] flex flex-col justify-between transition-all duration-300 hover:scale-[1.02]">
          <div>
            <div className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Cycles</div>
            <div className="font-mono text-xl font-black text-slate-100 mt-1">{reliability.cycle_count ?? 0}</div>
            <div className="font-mono text-[8px] uppercase tracking-[0.12em] text-indigo-400 mt-0.5">Completed</div>
          </div>
          <RingProgressIcon />
        </div>

        <div className="surface-card border border-white/5 p-4 relative overflow-hidden bg-zinc-950/45 min-h-[95px] flex flex-col justify-between transition-all duration-300 hover:scale-[1.02]">
          <div>
            <div className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Avg Cycle</div>
            <div className="font-mono text-xl font-black text-slate-100 mt-1">{(reliability.avg_cycle_duration_sec ?? 0).toFixed(2)}s</div>
            <div className="font-mono text-[8px] uppercase tracking-[0.12em] text-fuchsia-400 mt-0.5">Latency</div>
          </div>
          <LatencyWaveIcon />
        </div>
      </div>

      <div className="relative overflow-hidden border border-white/5 bg-zinc-950/35 p-4 min-h-[190px] transition-all duration-300 hover:border-emerald-500/20">
        <WorldMapIllustration />
        <div className="relative z-10">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Commodity Coverage</span>
            <Database className="h-3.5 w-3.5 text-zinc-500" />
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 max-w-md">
            {quickHealth?.commodities_with_intelligence?.map((commodity: string) => (
              <div key={commodity} className="flex items-center justify-between border-b border-white/[0.03] py-1">
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-zinc-400">{commodity}</span>
                <StatusDot ok pulse />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="border border-white/5 bg-zinc-950/35 p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Live Event Stream</span>
          <Signal className="h-3.5 w-3.5 text-cyan-300/70" />
        </div>
        <div className="max-h-60 overflow-y-auto pr-1">
          <EventFeed events={cognitionEvents.slice(0, 12)} />
        </div>
      </div>

      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500">Latest sync: {latestUpdate ? formatTime((latestUpdate as any).timestamp || new Date()) : 'Awaiting event feed'}</div>
      <div className="pointer-events-none absolute top-1/2 right-0 w-36 h-36 opacity-10 filter blur-[35px] bg-violet-500/20 rounded-full -mr-16 z-0" />
    </div>
  );
}

function SkeletonViewport() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
      <div className="relative h-14 w-14 border border-cyan-300/20 bg-cyan-300/5">
        <span className="absolute inset-4 animate-ping bg-cyan-300/25" />
        <BrainCircuit className="absolute left-1/2 top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 text-cyan-300/70" />
      </div>
      <div>
        <div className="font-mono text-[11px] font-bold uppercase tracking-[0.28em] text-zinc-500">Awaiting intelligence synthesis</div>
        <div className="mt-2 text-sm text-zinc-700">Run seed or wait for the cognition layer to publish market states.</div>
      </div>
    </div>
  );
}

export default function TraderOS() {
  const stream = useCognitionStream();
  const {
    status,
    latestUpdate: rawLatestUpdate,
    allStates: rawAllStates,
    auditLog: rawAuditLog,
    memories: rawMemories,
    systemHealth: rawSystemHealth,
    cognitionEvents: rawCognitionEvents,
    queryResult: rawQueryResult,
    isQuerying,
    isSeeding,
    quickHealth: rawQuickHealth,
    submitQuery,
    seedCognition,
    triggerRefresh,
  } = stream;

  const allStates = rawAllStates as MarketState[];
  const auditLog = rawAuditLog as AuditEntry[];
  const memories = rawMemories as MemoryEntry[];
  const systemHealth = rawSystemHealth as SystemHealth | null;
  const cognitionEvents = rawCognitionEvents as CognitionEvent[];
  const quickHealth = rawQuickHealth as QuickHealth | null;
  const queryResult = rawQueryResult as QueryResult | null;
  const latestUpdate = rawLatestUpdate;

  const [activeIdx, setActiveIdx] = useState(0);
  const [view, setView] = useState<ViewMode>('INTELLIGENCE');
  const [clock, setClock] = useState('');

  useEffect(() => {
    setClock(formatTime(new Date()));
    const timer = setInterval(() => setClock(formatTime(new Date())), 1000);
    return () => clearInterval(timer);
  }, []);

  const safeActiveIdx = allStates.length > 0 ? Math.min(activeIdx, allStates.length - 1) : 0;
  const activeState = allStates[safeActiveIdx] ?? null;
  const bestState = useMemo(() => selectStrongestOpportunity(allStates), [allStates]);
  const heroState = bestState ?? activeState;
  const isLive = status === 'LIVE';
  const activeDirective = getDirective(activeState?.directives);
  const formattedMandi = heroState?.mandi_id?.replace(/_/g, ' ');
  const contextLabel = heroState
    ? `${heroState.commodity?.toUpperCase() ?? 'MARKET'} / ${formattedMandi?.toUpperCase() ?? 'UNKNOWN'}`
    : 'NO ACTIVE MARKET';

  const tabs = useMemo(
    () => [
      { id: 'INTELLIGENCE' as const, icon: BrainCircuit },
      { id: 'QUERY' as const, icon: Command },
      { id: 'EVENTS' as const, icon: Activity },
    ],
    [],
  );

  return (
    <div className="traderos h-screen w-full overflow-hidden bg-black text-zinc-100">
      <div className="flex h-full flex-col bg-[radial-gradient(circle_at_24%_0%,rgba(8,145,178,0.14),transparent_36%),linear-gradient(180deg,#050506_0%,#000_48%,#030304_100%)]">
        <header className="shrink-0 border-b border-white/[0.07] bg-black/80 backdrop-blur-xl">
          <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-5 py-3">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center border border-cyan-300/25 bg-cyan-300/8 shadow-[0_0_30px_rgba(34,211,238,0.12)]">
                <Layers3 className="h-5 w-5 text-cyan-200" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-black tracking-tight text-zinc-50">TraderOS</span>
                  <span className="border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-[8px] font-bold uppercase tracking-[0.22em] text-zinc-500">Ag Intelligence Command Center</span>
                </div>
                <div className="mt-0.5 truncate font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-300/70">{contextLabel}</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {tabs.map((tab) => (
                <Button key={tab.id} icon={tab.icon} variant="tertiary" active={view === tab.id} onClick={() => setView(tab.id)}>
                  {tab.id}
                </Button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <div className="hidden items-center gap-2 border border-zinc-900 bg-zinc-950/70 px-3 py-2 md:flex">
                <StatusDot ok={isLive} pulse={isLive} />
                <span className="font-mono text-[9px] font-bold uppercase tracking-[0.22em] text-zinc-400">WS {status}</span>
              </div>
              <Button onClick={seedCognition} disabled={isSeeding} variant="secondary" icon={Play}>
                {isSeeding ? 'Seeding' : 'Seed'}
              </Button>
              <Button onClick={triggerRefresh} variant="primary" icon={RefreshCw}>
                Refresh
              </Button>
              <span className="hidden w-24 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-600 lg:block">{clock}</span>
            </div>
          </div>
        </header>

        {allStates.length > 0 && (
          <nav className="shrink-0 border-b border-white/[0.06] bg-zinc-950/80 select-none">
            <div className="flex overflow-x-auto scrollbar-none">
              {allStates.map((state, index) => {
                const selected = index === safeActiveIdx;
                const directive = getDirective(state.directives);
                const action = directive?.primary_directive ?? 'SYNTHESIZING';
                const upperAction = action.toUpperCase();
                
                let trendText = 'PRICE IS EXPECTED TO STABLE →';
                let trendColor = 'text-amber-400';
                let dotColorClass = 'bg-amber-400';
                let borderClass = 'ticker-stable';

                if (upperAction.includes('UP') || upperAction.includes('BUY') || upperAction.includes('ACCUMULATE')) {
                  trendText = 'PRICE IS EXPECTED TO UPWARD ↑';
                  trendColor = 'text-emerald-400';
                  dotColorClass = 'bg-emerald-400';
                  borderClass = 'ticker-bullish';
                } else if (upperAction.includes('DOWN') || upperAction.includes('SELL')) {
                  trendText = 'PRICE IS EXPECTED TO DOWNWARD ↓';
                  trendColor = 'text-rose-400';
                  dotColorClass = 'bg-rose-400';
                  borderClass = 'ticker-bearish';
                }
                
                return (
                  <button
                    key={`${state.commodity}-${state.mandi_id}-${index}`}
                    onClick={() => setActiveIdx(index)}
                    className={cx(
                      'group relative min-w-56 border-r border-white/[0.06] px-4 py-3.5 text-left transition-all duration-300',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-inset',
                      borderClass,
                      selected ? 'bg-zinc-900/50 ticker-active' : 'hover:bg-zinc-900/40',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={cx('font-mono text-[10px] font-black uppercase tracking-[0.18em]', selected ? 'text-zinc-50 font-bold' : 'text-zinc-400 group-hover:text-zinc-200')}>{state.commodity}</span>
                      <span className="relative inline-flex h-2 w-2 items-center justify-center">
                        {selected && <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 bg-current" style={{ color: trendColor === 'text-emerald-400' ? '#34d399' : trendColor === 'text-rose-400' ? '#fb7185' : '#fbbf24' }} />}
                        <span className={cx('relative h-1.5 w-1.5 rounded-full', dotColorClass)} />
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[9px] font-medium uppercase tracking-[0.12em] text-zinc-500">{state.mandi_id?.replace('_apmc', ' APMC').replace(/_/g, ' ')}</div>
                    <div className={cx("mt-2 truncate font-mono text-[8px] font-bold uppercase tracking-[0.1em]", trendColor)}>{trendText}</div>
                    {selected && <span className="absolute inset-x-0 bottom-0 h-0.5 bg-current shadow-[0_0_18px_rgba(34,211,238,0.8)]" style={{ color: trendColor === 'text-emerald-400' ? '#34d399' : trendColor === 'text-rose-400' ? '#fb7185' : '#fbbf24' }} />}
                  </button>
                );
              })}
            </div>
          </nav>
        )}

        <main className="grid min-h-0 flex-1 grid-cols-1 gap-px bg-white/[0.06] xl:grid-cols-[320px_minmax(0,1fr)_360px]">
          <aside className="panel-archive hidden min-h-0 flex-col bg-zinc-950/80 xl:flex border-r border-white/5">
            <SectionHeader icon={Archive} title="Operational Log" meta="lineage" tier="T3" />
            <div className="min-h-0 flex-1 overflow-y-auto">
              <AuditPanel auditLog={auditLog} memories={memories} />
            </div>
          </aside>

          <section className="panel-viewport min-h-0 bg-zinc-950/50">
            <div className="flex h-full flex-col">
              <SectionHeader
                icon={view === 'INTELLIGENCE' ? BrainCircuit : view === 'QUERY' ? Command : Activity}
                title="Command Center"
                meta={`${view} / ${contextLabel}`}
                tier="T1"
              />
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                {view === 'INTELLIGENCE' && (
                  <div className="space-y-4">
                    {heroState ? <PrimaryRegime state={heroState} /> : <div className="h-[60vh]"><SkeletonViewport /></div>}
                    {allStates.length > 0 && (
                      <section className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-500">All Active Markets</div>
                          <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zinc-700">{allStates.length} contexts</div>
                        </div>
                        <div className="grid gap-3 2xl:grid-cols-3 md:grid-cols-2">
                          {allStates.map((state, index) => (
                            <MarketCard key={`${state.commodity}-${state.mandi_id}-${index}`} state={state} active={index === safeActiveIdx} onClick={() => setActiveIdx(index)} />
                          ))}
                        </div>
                      </section>
                    )}
                  </div>
                )}

                {view === 'QUERY' && (
                  <div className="mx-auto max-w-5xl space-y-5">
                    <div className="border border-zinc-900 bg-zinc-950/45 p-5">
                      <div className="mb-2 flex items-center gap-2">
                        <Zap className="h-4 w-4 text-cyan-300" />
                        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-zinc-400">Institutional Command Console</span>
                      </div>
                      <p className="max-w-2xl text-sm leading-6 text-zinc-500">Ask the live intelligence layer for sell timing, mandi risk, commodity strength, and tactical guidance.</p>
                    </div>
                    <QueryConsole onSubmit={submitQuery} result={queryResult} isQuerying={isQuerying} />
                  </div>
                )}

                {view === 'EVENTS' && (
                  <div className="mx-auto max-w-5xl space-y-4">
                    <div className="grid gap-3 md:grid-cols-3">
                      <MetricTile label="Stream" value={status} sub="websocket" tone={isLive ? 'stable' : 'risk'} />
                      <MetricTile label="Events" value={cognitionEvents.length} sub="session" tone="neutral" />
                      <MetricTile label="Active" value={activeDirective?.action_code ?? 'N/A'} sub={activeState?.commodity ?? 'market'} tone={actionTone(activeDirective?.primary_directive ?? '')} />
                    </div>
                    <EventFeed events={cognitionEvents} large />
                  </div>
                )}
              </div>
            </div>
          </section>

          <aside className="panel-recovery hidden min-h-0 flex-col bg-zinc-950/80 xl:flex border-l border-white/5">
            <SectionHeader icon={ShieldCheck} title="System Health" meta="health" tier="T2" />
            <div className="min-h-0 flex-1 overflow-y-auto">
              <HealthPanel systemHealth={systemHealth} cognitionEvents={cognitionEvents} allStates={allStates} quickHealth={quickHealth} latestUpdate={latestUpdate} />
            </div>
          </aside>
        </main>

        <footer className="flex min-h-8 shrink-0 items-center justify-between border-t border-white/[0.06] bg-zinc-950 px-5 py-2">
          <div className="flex items-center gap-5 font-mono text-[8px] uppercase tracking-[0.2em] text-zinc-500">
            <span className="flex items-center gap-1.5 text-zinc-400"><Gauge className="h-3 w-3 text-cyan-400" /> Enterprise v1</span>
            <span className="flex items-center gap-1.5"><BarChart3 className="h-3 w-3 text-emerald-400" /> States {allStates.length}</span>
            <span className="flex items-center gap-1.5"><Activity className="h-3 w-3 text-fuchsia-400" /> Events {cognitionEvents.length}</span>
          </div>
          <div className="font-mono text-[8px] uppercase tracking-[0.2em] text-cyan-300/80 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping inline-block" /> Context locked: {contextLabel}
          </div>
        </footer>
      </div>
    </div>
  );
}
