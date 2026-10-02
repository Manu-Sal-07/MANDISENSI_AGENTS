'use client';

/**
 * Trading desk home.
 *
 * The trader-side front door: a live price chart for the chosen crop, the numbers
 * a trader checks first (price, 7- and 30-day move, spread between the best and
 * worst mandi), a tape of every crop in the district, and a launchpad into the
 * five desk modules. Everything numeric comes from the same recorded Agmarknet
 * endpoints the farmer app reads; the module illustrations are decorative.
 */

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, Bot, FlaskConical, LineChart, Terminal, TrendingDown, TrendingUp, Wrench } from 'lucide-react';

import CountUp from '@/components/farm/charts/CountUp';
import { useFarm } from '@/context/FarmContext';
import { farmerApi } from '@/services/farmerApi';

const EN = new Intl.NumberFormat('en-IN');
const money = (n: number) => `₹${EN.format(Math.round(n))}`;
const CROP_NAME = (c: string) => c.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());

/* ── chart: the selected crop's recorded price history ── */
function PriceChart({ points }: { points: Array<{ d: string; p: number }> }) {
  const reduce = useReducedMotion();
  const W = 640;
  const H = 260;
  const pad = 14;
  const lo = Math.min(...points.map((x) => x.p));
  const hi = Math.max(...points.map((x) => x.p));
  const span = hi - lo || 1;
  const xy = points.map((x, i) => [pad + (i / (points.length - 1)) * (W - pad * 2), H - pad - ((x.p - lo) / span) * (H - pad * 2 - 10)] as const);
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area = `${line} L${xy[xy.length - 1][0]} ${H} L${xy[0][0]} ${H}Z`;
  const [lx, ly] = xy[xy.length - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Recorded price history">
      <defs>
        <linearGradient id="dh-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--tb-cyan)" stopOpacity="0.32" />
          <stop offset="1" stopColor="var(--tb-cyan)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1={pad} x2={W - pad} y1={pad + f * (H - pad * 2)} y2={pad + f * (H - pad * 2)} stroke="var(--surface-border)" strokeDasharray="3 6" />
      ))}
      <motion.path d={area} fill="url(#dh-area)" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9, duration: 0.8 }} />
      <motion.path
        d={line}
        fill="none"
        stroke="var(--tb-cyan)"
        strokeWidth="2.4"
        strokeLinejoin="round"
        strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
      />
      <circle cx={lx} cy={ly} r="9" fill="var(--tb-cyan)" opacity="0.2" className="tb-ping" />
      <circle cx={lx} cy={ly} r="4.5" fill="var(--tb-cyan)" stroke="var(--surface-0)" strokeWidth="2" />
      <text x={pad} y={12} className="tb-chart-label">{money(hi)}</text>
      <text x={pad} y={H - 4} className="tb-chart-label">{money(lo)}</text>
    </svg>
  );
}

/* ── module illustrations (decorative) ── */
function Viz({ kind }: { kind: string }) {
  if (kind === 'explorer')
    return (
      <svg viewBox="0 0 120 48" preserveAspectRatio="none" className="h-12 w-full">
        <path className="tb-draw" pathLength="1" d="M2 38 C18 36 22 14 38 20 C54 26 56 42 72 30 C88 18 92 8 118 12" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
    );
  if (kind === 'lab')
    return (
      <svg viewBox="0 0 64 48" className="h-12 w-full">
        <g className="tb-spin" style={{ transformOrigin: '32px 24px' }} fill="none" stroke="currentColor" strokeWidth="1.6">
          <polygon points="32,4 52,15 52,33 32,44 12,33 12,15" />
          <polygon points="32,12 45,19 45,29 32,36 19,29 19,19" opacity=".6" />
          <circle cx="32" cy="24" r="2.4" fill="currentColor" />
        </g>
      </svg>
    );
  if (kind === 'terminal')
    return (
      <div className="flex h-12 flex-col justify-center gap-1.5">
        {[70, 48, 60].map((w, i) => (
          <span key={i} className="tb-type block h-1.5 rounded-full bg-current" style={{ width: `${w}%`, animationDelay: `${i * 0.5}s` }} />
        ))}
      </div>
    );
  if (kind === 'tools')
    return (
      <div className="flex h-12 items-end gap-1.5">
        {[0.5, 0.9, 0.65, 1, 0.45, 0.8].map((h, i) => (
          <span key={i} className="tb-bar block w-3 rounded-sm bg-current" style={{ height: `${h * 100}%`, animationDelay: `${i * 0.18}s` }} />
        ))}
      </div>
    );
  return (
    <div className="flex h-12 flex-col justify-center gap-1.5">
      {[100, 82, 56].map((w, i) => (
        <span key={i} className="tb-shimmer block h-1.5 rounded-full" style={{ width: `${w}%`, animationDelay: `${i * 0.3}s` }} />
      ))}
    </div>
  );
}

const MODULES = [
  { href: '/market-explorer', title: 'Market Explorer', blurb: 'Price history, seasonality, commodity DNA and forecasts for any mandi.', icon: LineChart, accent: 'cyan', viz: 'explorer', photo: 'desk-hall' },
  { href: '/intelligence-lab', title: 'Intelligence Lab', blurb: 'Hidden opportunities, historical analogs and counterfactual simulations.', icon: FlaskConical, accent: 'violet', viz: 'lab', photo: 'desk-night' },
  { href: '/terminal', title: 'Command Center', blurb: 'The full-screen operations terminal for the multi-agent engine.', icon: Terminal, accent: 'green', viz: 'terminal', photo: 'desk-truck' },
  { href: '/trader-tools', title: 'Trader Tools', blurb: 'Mandi spreads, volatility regime, scenarios, forward price and position risk.', icon: Wrench, accent: 'amber', viz: 'tools', photo: 'desk-scale' },
  { href: '/ai-brief', title: 'AI Brief', blurb: 'An evidence-checked decision brief for one commodity at one mandi.', icon: Bot, accent: 'cyan', viz: 'brief', photo: 'desk-tomatoes' },
] as const;

export default function TraderDeskPage() {
  const { district, crop, setCrop } = useFarm();

  const { data: overview } = useQuery({ queryKey: ['farm-overview', district], queryFn: () => farmerApi.overview(district) });
  const { data: board, isLoading } = useQuery({ queryKey: ['farm-board', district, crop], queryFn: () => farmerApi.board(district, crop) });

  const ok = board && board.status === 'OK';
  const hist = ok ? board.history.slice(-120) : [];
  const prices = ok ? board.mandis.map((m) => m.price) : [];
  const spread = prices.length > 1 ? Math.max(...prices) - Math.min(...prices) : null;

  const stats: Array<{ label: string; node: React.ReactNode; tone?: 'up' | 'down' }> = ok
    ? [
        { label: 'Price / qtl', node: <CountUp value={board.price.value} /> },
        { label: '7-day move', node: board.changes.d7 == null ? '—' : `${board.changes.d7 >= 0 ? '+' : ''}${board.changes.d7.toFixed(1)}%`, tone: board.changes.d7 == null ? undefined : board.changes.d7 >= 0 ? 'up' : 'down' },
        { label: '30-day move', node: board.changes.d30 == null ? '—' : `${board.changes.d30 >= 0 ? '+' : ''}${board.changes.d30.toFixed(1)}%`, tone: board.changes.d30 == null ? undefined : board.changes.d30 >= 0 ? 'up' : 'down' },
        { label: 'Mandi spread', node: spread == null ? '—' : money(spread) },
        { label: 'Mandis quoting', node: String(board.mandis.length) },
      ]
    : [];

  return (
    <div className="min-h-screen overflow-x-clip pb-24 md:pb-16">
      <div className="mx-auto max-w-[1480px] px-4 pt-8 sm:px-6">
        {/* hero */}
        <section className="tb-hero tb-accent-cyan relative overflow-hidden rounded-[2rem] p-5 sm:p-8 lg:p-10">
          <div className="tb-slides" aria-hidden="true">
            {['desk-yard', 'desk-hall', 'desk-unload', 'desk-night'].map((n, i) => (
              <span key={n} className="tb-slide" style={{ backgroundImage: `url(/photos/${n}.jpg)`, animationDelay: `${i * 8}s` }} />
            ))}
          </div>
          <div className="tb-hero-scrim" aria-hidden="true" />
          <div className="tb-hero-glow" aria-hidden="true" />
          <div className="relative z-10 grid min-w-0 grid-cols-1 items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
            <div>
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="tb-live inline-flex max-w-full items-center gap-2 rounded-full px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-[0.18em]"
              >
                <span className="live-dot shrink-0" /> <span>Trading desk<span className="hidden sm:inline"> · recorded Agmarknet prices</span></span>
              </motion.p>
              <motion.h1
                initial={{ opacity: 0, y: 22 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="font-display mt-5 text-[clamp(2.3rem,5.4vw,4.6rem)] font-black leading-[1.02] tracking-tight text-foreground"
              >
                Read the spread <span className="tb-gradient-text">before the market moves.</span>
              </motion.h1>
              <p className="mt-4 max-w-[52ch] text-[15px] leading-relaxed text-neutral-signal sm:text-base">
                Mandi spreads, volatility regimes, historical analogs, scenarios and evidence-checked briefs, built on the same recorded prices the farmer app uses.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href="/market-explorer" className="tb-cta farm-focus inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold">
                  Open Explorer <ArrowUpRight className="h-4 w-4" />
                </Link>
                <Link href="/trader-tools" className="tb-ghost farm-focus inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold">
                  Trader tools
                </Link>
              </div>
            </div>

            {/* live chart panel */}
            <div className="tb-panel relative rounded-3xl p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Crop">
                  {(overview?.crops ?? []).map((c) => (
                    <button
                      key={c.crop}
                      role="tab"
                      aria-selected={c.crop === crop}
                      onClick={() => setCrop(c.crop)}
                      className={`tb-chip farm-focus rounded-lg px-3 py-1.5 text-xs font-bold ${c.crop === crop ? 'tb-chip-on' : ''}`}
                    >
                      {CROP_NAME(c.crop)}
                    </button>
                  ))}
                </div>
                {ok && <span className="text-[11px] font-semibold text-neutral-signal">{board.district_name?.en ?? board.district} · to {board.price.date}</span>}
              </div>
              <div className="mt-3 h-[230px] sm:h-[260px]">
                {isLoading && <div className="tb-skel h-full w-full rounded-2xl" />}
                {!isLoading && hist.length > 2 && <PriceChart key={`${district}-${crop}`} points={hist} />}
                {!isLoading && !hist.length && <p className="flex h-full items-center justify-center text-sm text-neutral-signal">No recorded price history for this series.</p>}
              </div>
            </div>
          </div>
        </section>

        {/* numbers a trader checks first */}
        {stats.length > 0 && (
          <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {stats.map((s, i) => (
              <motion.li
                key={s.label}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.06 }}
                className="tb-panel rounded-2xl px-4 py-3.5"
              >
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-signal">{s.label}</p>
                <p
                  className="font-display mt-1 flex items-center gap-1.5 text-2xl font-black tabular-nums"
                  style={{ color: s.tone === 'up' ? 'var(--bullish)' : s.tone === 'down' ? 'var(--bearish)' : 'var(--foreground)' }}
                >
                  {s.tone === 'up' && <TrendingUp className="h-5 w-5" />}
                  {s.tone === 'down' && <TrendingDown className="h-5 w-5" />}
                  {s.node}
                </p>
              </motion.li>
            ))}
          </ul>
        )}

        {/* tape */}
        {overview?.crops?.length ? (
          <div className="tb-tape tb-panel relative mt-4 overflow-hidden rounded-2xl py-3" role="region" aria-label="District crop prices">
            <ul className="tb-tape-track flex w-max items-center">
              {[0, 1, 2, 3].map((copy) =>
                overview.crops.map((c) => {
                  const up = (c.d7 ?? 0) >= 0;
                  return (
                    <li key={`${copy}-${c.crop}`} aria-hidden={copy > 0 || undefined} className="flex shrink-0 items-center gap-3 px-6 text-sm">
                      <span className="font-bold uppercase tracking-wider text-neutral-signal">{CROP_NAME(c.crop)}</span>
                      <span className="font-mono font-bold tabular-nums text-foreground">{money(c.price)}</span>
                      {c.d7 != null && (
                        <span className="font-mono text-xs font-bold tabular-nums" style={{ color: up ? 'var(--bullish)' : 'var(--bearish)' }}>
                          {up ? '▲' : '▼'} {Math.abs(c.d7).toFixed(1)}%
                        </span>
                      )}
                      <span className="text-neutral-signal/40" aria-hidden="true">/</span>
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        ) : null}

        {/* modules */}
        <h2 className="font-display mt-12 text-[11px] font-bold uppercase tracking-[0.3em] text-neutral-signal">Desk modules</h2>
        <ul className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {MODULES.map((m, i) => {
            const Icon = m.icon;
            return (
              <motion.li
                key={m.href}
                initial={{ opacity: 0, y: 26 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.55, delay: (i % 3) * 0.08, ease: [0.16, 1, 0.3, 1] }}
                className={i === 0 ? 'xl:col-span-2' : ''}
              >
                <Link href={m.href} className={`tb-module tb-accent-${m.accent} farm-focus group relative block h-full overflow-hidden rounded-3xl`}>
                  <span className="tb-module-img" style={{ backgroundImage: `url(/photos/${m.photo}.jpg)` }} aria-hidden="true" />
                  <span className="tb-module-scrim" aria-hidden="true" />
                  <span className="relative z-10 flex min-h-[15rem] flex-col justify-between p-5 sm:min-h-[17rem] sm:p-6">
                    <span className="flex items-start justify-between">
                      <span className="tb-hero-icon tb-icon-solid flex h-12 w-12 items-center justify-center rounded-2xl">
                        <Icon className="h-6 w-6" />
                      </span>
                      <span className="tb-arrow flex h-10 w-10 items-center justify-center rounded-full">
                        <ArrowUpRight className="h-5 w-5" />
                      </span>
                    </span>
                    <span>
                      <span className="tb-accent-text block max-w-[10rem] opacity-90">
                        <Viz kind={m.viz} />
                      </span>
                      <span className="font-display mt-3 block text-2xl font-black tracking-tight text-white sm:text-3xl">{m.title}</span>
                      <span className="mt-1 block max-w-[48ch] text-sm leading-relaxed text-white/80">{m.blurb}</span>
                    </span>
                  </span>
                </Link>
              </motion.li>
            );
          })}
        </ul>

        <p className="mt-10 text-center text-[11px] leading-relaxed text-neutral-signal">
          Photos via Wikimedia Commons: Sntshkumar750 (CC BY-SA 4.0), McKay Savage (CC BY 2.0), Prateek Rungta (CC BY 2.0), John Hoey (CC BY 2.0), எஸ்ஸார் (CC BY-SA 3.0).
        </p>
      </div>
    </div>
  );
}
