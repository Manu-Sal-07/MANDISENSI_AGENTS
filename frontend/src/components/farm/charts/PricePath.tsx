'use client';

import React, { useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

import { useLanguage } from '@/context/LanguageContext';
import { rupees, say, shortDate } from '@/lib/i18n/farmCopy';
import type { FarmBoard } from '@/services/farmerApi';
import { toneOf } from '../callTone';
import { useWidth } from './useWidth';

/**
 * The price path.
 *
 * Solid ink is what was recorded. The dashed line is the same stretch a year
 * earlier. To the right of "today" the forecast is drawn as a corridor that
 * widens with the days: the darker band is where the price is about as likely
 * to be as not, the faint one where it is nearly certain to stay. Uncertainty
 * is the shape of the picture, not a footnote under it.
 *
 * The forward zone is stretched (seven days get the last 30% of the width) —
 * at true scale a week of a four-month chart is a sliver too thin to read.
 */

const HISTORY_DAYS = 75;
const FORWARD_SHARE = 0.3;
const H = 270;
const M = { top: 22, right: 12, bottom: 28, left: 12 };

type Hover = { kind: 'past'; i: number } | { kind: 'future'; day: number } | null;

const day = (iso: string) => Date.parse(iso) / 86_400_000;

export default function PricePath({ board }: { board: FarmBoard }) {
  const { lang } = useLanguage();
  const reduce = useReducedMotion();
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<Hover>(null);
  const tone = toneOf(board.call, lang);

  const model = useMemo(() => {
    const hist = board.history.slice(-HISTORY_DAYS);
    const t0 = day(hist[0].d);
    const tEnd = day(hist[hist.length - 1].d);
    const ly = board.history_last_year.filter((p) => day(p.d) >= t0 && day(p.d) <= tEnd);
    const fc = board.forecast.filter((f) => f.price != null && f.p25 != null && f.p75 != null);

    const prices = [...hist.map((p) => p.p), ...ly.map((p) => p.p), ...fc.flatMap((f) => [f.p25!, f.p75!, f.price!])];
    const lo = Math.min(...prices);
    const hi = Math.max(...prices);
    const pad = (hi - lo) * 0.1 || hi * 0.05;
    return { hist, t0, tEnd, ly, fc, yLo: Math.max(0, lo - pad), yHi: hi + pad };
  }, [board]);

  const plotW = Math.max(120, width - M.left - M.right);
  const plotH = H - M.top - M.bottom;
  const pastW = plotW * (1 - FORWARD_SHARE);
  const x = (t: number) => M.left + ((t - model.t0) / Math.max(1, model.tEnd - model.t0)) * pastW;
  const xf = (d: number) => M.left + pastW + (d / 7) * plotW * FORWARD_SHARE;
  const y = (p: number) => M.top + (1 - (p - model.yLo) / (model.yHi - model.yLo)) * plotH;
  const todayX = M.left + pastW;

  const line = (pts: Array<[number, number]>) => pts.map(([a, b], i) => `${i ? 'L' : 'M'}${a.toFixed(1)} ${b.toFixed(1)}`).join(' ');
  const histPts = model.hist.map((p) => [x(day(p.d)), y(p.p)] as [number, number]);
  const lyPts = model.ly.map((p) => [x(day(p.d)), y(p.p)] as [number, number]);
  const last = model.hist[model.hist.length - 1];
  const start: [number, number] = [todayX, y(last.p)];

  const band = (lowKey: 'p25' | 'p05', highKey: 'p75' | 'p95') => {
    const top = [start, ...model.fc.map((f) => [xf(f.horizon), y(f[highKey] ?? f.p75!)] as [number, number])];
    const bottom = [...model.fc.map((f) => [xf(f.horizon), y(f[lowKey] ?? f.p25!)] as [number, number])].reverse();
    return `${line(top)} L${bottom.map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(' L')} L${start[0]} ${start[1]} Z`;
  };
  const centre = line([start, ...model.fc.map((f) => [xf(f.horizon), y(f.price!)] as [number, number])]);

  const ticks = useMemo(() => {
    const n = 3;
    return Array.from({ length: n }, (_, i) => model.yLo + ((model.yHi - model.yLo) * (i + 0.5)) / n);
  }, [model]);

  const months = useMemo(() => {
    const out: Array<{ t: number; label: string }> = [];
    const d = new Date(model.t0 * 86_400_000);
    d.setUTCDate(1);
    d.setUTCMonth(d.getUTCMonth() + 1);
    while (d.getTime() / 86_400_000 < model.tEnd - 6) {
      out.push({
        t: d.getTime() / 86_400_000,
        label: d.toLocaleDateString(lang === 'kn' ? 'kn-IN' : lang === 'hi' ? 'hi-IN' : 'en-IN', { month: 'short', timeZone: 'UTC' }),
      });
      d.setUTCMonth(d.getUTCMonth() + 1);
    }
    return out;
  }, [model, lang]);

  const onMove = (event: React.PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - rect.left;
    if (px >= todayX - M.left + 4 && model.fc.length) {
      const d = Math.max(1, Math.min(7, Math.round(((px - (todayX - M.left)) / (plotW * FORWARD_SHARE)) * 7)));
      setHover({ kind: 'future', day: d });
    } else {
      const t = model.t0 + (px / pastW) * (model.tEnd - model.t0);
      let best = 0;
      model.hist.forEach((p, i) => {
        if (Math.abs(day(p.d) - t) < Math.abs(day(model.hist[best].d) - t)) best = i;
      });
      setHover({ kind: 'past', i: best });
    }
  };

  const futureAt = (d: number) => model.fc.reduce((a, b) => (Math.abs(b.horizon - d) < Math.abs(a.horizon - d) ? b : a));

  let tip: { x: number; title: string; lines: string[] } | null = null;
  if (hover?.kind === 'past') {
    const p = model.hist[hover.i];
    const same = model.ly.reduce<typeof model.ly[number] | null>(
      (a, b) => (!a || Math.abs(day(b.d) - day(p.d)) < Math.abs(day(a.d) - day(p.d)) ? b : a),
      null
    );
    tip = {
      x: x(day(p.d)),
      title: shortDate(p.d, lang),
      lines: [`${say('chart.thisYear', lang)}: ${rupees(p.p)}`, ...(same && Math.abs(day(same.d) - day(p.d)) < 4 ? [`${say('chart.lastYear', lang)}: ${rupees(same.p)}`] : [])],
    };
  } else if (hover?.kind === 'future') {
    const f = futureAt(hover.day);
    tip = {
      x: xf(f.horizon),
      title: f.date ? shortDate(f.date, lang) : '',
      lines: [`${say('chart.likely', lang)}: ${rupees(f.price)}`, `${rupees(f.p25)} – ${rupees(f.p75)}`],
    };
  }

  const summary = `${rupees(last.p)} ${say('unit.qtl', lang)}. ${model.fc.length ? `${say('chart.next', lang)}: ${rupees(model.fc[model.fc.length - 1].p25)} – ${rupees(model.fc[model.fc.length - 1].p75)}.` : ''}`;
  const draw = reduce ? { pathLength: 1 } : undefined;

  return (
    <div ref={ref} className="relative select-none">
      <svg width={width} height={H} role="img" aria-label={summary} className="block touch-pan-y overflow-visible">
        <defs>
          <linearGradient id="pp-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--leaf)" stopOpacity="0.16" />
            <stop offset="100%" stopColor="var(--leaf)" stopOpacity="0" />
          </linearGradient>
          <clipPath id="pp-forward">
            <motion.rect
              x={todayX}
              y={0}
              height={H}
              initial={reduce ? { width: plotW * FORWARD_SHARE + M.right } : { width: 0 }}
              animate={{ width: plotW * FORWARD_SHARE + M.right }}
              transition={{ delay: 0.85, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            />
          </clipPath>
        </defs>

        {/* The forward zone is tinted so "not yet happened" is visible at a glance. */}
        <rect x={todayX} y={M.top - 8} width={plotW * FORWARD_SHARE + M.right} height={plotH + 8} rx={14} fill={tone.wash} opacity={0.7} />

        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} stroke="var(--farm-line)" strokeDasharray="2 5" />
            <text x={M.left} y={y(t) - 5} fontSize={11} fill="var(--farm-ink-faint)" stroke="var(--farm-paper)" strokeWidth={3} paintOrder="stroke">{rupees(t)}</text>
          </g>
        ))}
        {months.map((m) => (
          <text key={m.t} x={x(m.t)} y={H - 8} fontSize={11} fill="var(--farm-ink-faint)" textAnchor="middle">{m.label}</text>
        ))}

        {lyPts.length > 1 && (
          <path d={line(lyPts)} fill="none" stroke="var(--farm-ink-faint)" strokeWidth={1.5} strokeDasharray="4 4" strokeLinecap="round" opacity={0.85} />
        )}

        <motion.path
          d={`${line(histPts)} L${todayX} ${M.top + plotH} L${histPts[0][0]} ${M.top + plotH} Z`}
          fill="url(#pp-fill)"
          initial={{ opacity: reduce ? 1 : 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
        />
        <motion.path
          d={line(histPts)}
          fill="none"
          stroke="var(--farm-ink)"
          strokeWidth={2.25}
          strokeLinejoin="round"
          strokeLinecap="round"
          initial={reduce ? draw : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.95, ease: [0.16, 1, 0.3, 1] }}
        />

        {model.fc.length > 0 && (
          <g clipPath="url(#pp-forward)">
            <path d={band('p05', 'p95')} fill={tone.colour} opacity={0.1} />
            <path d={band('p25', 'p75')} fill={tone.colour} opacity={0.24} />
            <path d={centre} fill="none" stroke={tone.colour} strokeWidth={2.25} strokeDasharray="5 4" strokeLinecap="round" />
          </g>
        )}

        <line x1={todayX} x2={todayX} y1={M.top - 8} y2={M.top + plotH} stroke="var(--farm-ink)" strokeWidth={1} opacity={0.35} />
        <text x={todayX - 6} y={M.top - 10} fontSize={11} fontWeight={700} fill="var(--farm-ink-soft)" textAnchor="end">{say('chart.today', lang)}</text>

        <circle cx={start[0]} cy={start[1]} r={5.5} fill="var(--farm-ink)" stroke="var(--farm-paper)" strokeWidth={2.5} />

        {hover && tip && (
          <g pointerEvents="none">
            <line x1={tip.x} x2={tip.x} y1={M.top - 8} y2={M.top + plotH} stroke="var(--farm-ink)" strokeWidth={1} opacity={0.5} />
            {hover.kind === 'past' && (
              <circle cx={tip.x} cy={y(model.hist[hover.i].p)} r={4.5} fill="var(--farm-ink)" stroke="var(--farm-paper)" strokeWidth={2} />
            )}
          </g>
        )}

        <rect
          x={M.left}
          y={0}
          width={plotW}
          height={H}
          fill="transparent"
          onPointerMove={onMove}
          onPointerDown={onMove}
          onPointerLeave={() => setHover(null)}
        />
      </svg>

      {tip && (
        <div
          className="pointer-events-none absolute top-0 z-10 rounded-xl border border-[var(--farm-line-strong)] bg-white px-3 py-2 text-xs shadow-[0_10px_28px_-14px_rgba(42,33,25,0.5)]"
          style={{ left: Math.min(Math.max(tip.x - 62, 0), width - 132), width: 124 }}
        >
          <p className="font-bold text-[var(--farm-ink)]">{tip.title}</p>
          {tip.lines.map((l) => (
            <p key={l} className="mt-0.5 tabular-nums text-[var(--farm-ink-soft)]">{l}</p>
          ))}
        </div>
      )}

      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5 px-1 text-xs text-[var(--farm-ink-soft)]">
        <li className="flex items-center gap-2"><span className="block h-0.5 w-5 rounded bg-[var(--farm-ink)]" />{say('chart.thisYear', lang)}</li>
        <li className="flex items-center gap-2"><span className="block w-5 border-t-2 border-dashed border-[var(--farm-ink-faint)]" />{say('chart.lastYear', lang)}</li>
        {model.fc.length > 0 && (
          <li className="flex items-center gap-2"><span className="block h-3 w-5 rounded-sm" style={{ background: tone.colour, opacity: 0.35 }} />{say('chart.next', lang)}</li>
        )}
      </ul>
      <p className="mt-1.5 px-1 text-[11px] text-[var(--farm-ink-faint)]">{say('chart.hint', lang)}</p>

      <table className="sr-only">
        <caption>{summary}</caption>
        <tbody>
          {model.hist.slice(-7).map((p) => (
            <tr key={p.d}><th>{p.d}</th><td>{rupees(p.p)}</td></tr>
          ))}
          {model.fc.map((f) => (
            <tr key={f.horizon}><th>{f.date}</th><td>{rupees(f.p25)} – {rupees(f.p75)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
