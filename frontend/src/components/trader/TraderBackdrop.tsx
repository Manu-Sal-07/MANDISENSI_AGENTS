'use client';

import React from 'react';
import { usePathname } from 'next/navigation';

import { isDeskRoute } from '@/lib/surfaces';

/**
 * The night-market scene behind every trader page: a perspective grid sliding
 * toward the viewer, two slow bands of candlesticks, a glowing price line that
 * redraws itself, drifting colour orbs and a faint scan beam. It is atmosphere
 * only (generated from a fixed seed, no data) and it holds still under
 * reduced motion.
 */

function candles(n: number, seed: number) {
  let s = seed;
  const rnd = () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
  let price = 100;
  return Array.from({ length: n }, (_, i) => {
    const open = price;
    const close = open + (rnd() - 0.47) * 16;
    const hi = Math.max(open, close) + rnd() * 9;
    const lo = Math.min(open, close) - rnd() * 9;
    price = close;
    return { i, open, close, hi, lo };
  });
}

const BAND_A = candles(70, 7);
const BAND_B = candles(70, 31);

function Band({ data, scale, offset }: { data: ReturnType<typeof candles>; scale: number; offset: number }) {
  const min = Math.min(...data.map((c) => c.lo));
  const y = (v: number) => 170 - (v - min) * scale + offset;
  const one = data.map((c) => {
    const up = c.close >= c.open;
    const x = c.i * 16 + 8;
    return (
      <g key={c.i} className={up ? 'tb-up' : 'tb-down'}>
        <line x1={x} x2={x} y1={y(c.hi)} y2={y(c.lo)} strokeWidth="1.4" />
        <rect x={x - 4} width="8" y={Math.min(y(c.open), y(c.close))} height={Math.max(2, Math.abs(y(c.open) - y(c.close)))} rx="1.5" />
      </g>
    );
  });
  return (
    <svg className="tb-band" viewBox={`0 0 ${data.length * 32} 200`} preserveAspectRatio="none" width={data.length * 32} height="200">
      <g>{one}</g>
      <g transform={`translate(${data.length * 16} 0)`}>{one}</g>
    </svg>
  );
}

export default function TraderBackdrop() {
  const pathname = usePathname();
  if (!isDeskRoute(pathname)) return null;

  return (
    <div className="tb" aria-hidden="true">
      <div className="tb-base" />
      <span className="tb-orb tb-orb-a" />
      <span className="tb-orb tb-orb-b" />
      <span className="tb-orb tb-orb-c" />

      <div className="tb-bandwrap tb-bandwrap-a">
        <Band data={BAND_A} scale={1.15} offset={0} />
      </div>
      <div className="tb-bandwrap tb-bandwrap-b">
        <Band data={BAND_B} scale={0.9} offset={10} />
      </div>

      <svg className="tb-line" viewBox="0 0 1440 220" preserveAspectRatio="none">
        <defs>
          <linearGradient id="tbl" x1="0" x2="1">
            <stop offset="0" stopColor="var(--tb-cyan)" stopOpacity="0" />
            <stop offset="0.5" stopColor="var(--tb-cyan)" />
            <stop offset="1" stopColor="var(--tb-violet)" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        <path
          className="tb-line-path"
          pathLength="1"
          d="M0 150 C90 140 130 90 210 110 C290 130 330 60 420 80 C520 104 560 170 660 140 C760 110 800 40 900 70 C1000 100 1040 160 1140 120 C1240 80 1300 90 1440 40"
          fill="none"
          stroke="url(#tbl)"
          strokeWidth="2.4"
          strokeLinecap="round"
        />
      </svg>

      <div className="tb-grid" />
      <div className="tb-scan" />
      <div className="tb-vignette" />
    </div>
  );
}
