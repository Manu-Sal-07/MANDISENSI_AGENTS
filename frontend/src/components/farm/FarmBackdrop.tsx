'use client';

import React from 'react';
import { usePathname } from 'next/navigation';

import { isFarmRoute } from '@/lib/surfaces';
import ProduceIcon from './ProduceIcon';

/**
 * The living scene behind every farmer page: a sunrise sky with slow clouds and
 * birds, hills carrying a row of market stalls, crop rows, a loaded truck
 * driving along the soil, drifting leaves and pollen, and (on wide screens, on
 * inner pages) framed photographs of farmers and mandi sellers flanking the
 * content column. Fixed to the viewport so content scrolls over it; CSS/SVG plus
 * four small JPEGs, and still under reduced-motion.
 */

const CLOUDS = [
  { top: '9%', w: 190, dur: '120s', delay: '-20s', op: 0.85 },
  { top: '19%', w: 130, dur: '160s', delay: '-90s', op: 0.65 },
  { top: '5%', w: 240, dur: '200s', delay: '-140s', op: 0.55 },
];

const MOTES = Array.from({ length: 14 }, (_, i) => ({
  left: `${(i * 37 + 9) % 100}%`,
  size: 3 + (i % 4),
  dur: `${22 + (i % 5) * 6}s`,
  delay: `${-(i * 3.3)}s`,
}));

const LEAVES = [
  { left: '6%', s: 18, dur: '34s', delay: '-4s' },
  { left: '31%', s: 14, dur: '41s', delay: '-19s' },
  { left: '57%', s: 17, dur: '37s', delay: '-27s' },
  { left: '82%', s: 13, dur: '45s', delay: '-11s' },
];

const FRAMES = [
  { side: 'l', top: '15vh', rot: -4, photo: 'farmer-smile', sticker: 'tomato', delay: '0s' },
  { side: 'l', top: '50vh', rot: 3, photo: 'vendor-stall', sticker: 'onion', delay: '-2s' },
  { side: 'r', top: '19vh', rot: 4, photo: 'mandi-yard', sticker: 'potato', delay: '-1s' },
  { side: 'r', top: '53vh', rot: -3, photo: 'seller-turban', sticker: 'garlic', delay: '-3s' },
] as const;

function Cloud({ w }: { w: number }) {
  return (
    <svg width={w} height={w * 0.42} viewBox="0 0 200 84" aria-hidden="true">
      <g fill="#fff">
        <ellipse cx="62" cy="56" rx="50" ry="22" />
        <ellipse cx="108" cy="44" rx="44" ry="28" />
        <ellipse cx="150" cy="58" rx="40" ry="20" />
        <ellipse cx="96" cy="62" rx="70" ry="18" />
      </g>
    </svg>
  );
}

function Bird({ x, y, s, d }: { x: number; y: number; s: number; d: string }) {
  return (
    <path
      className="farm-wing"
      style={{ animationDelay: d, transformOrigin: `${x}px ${y}px` }}
      d={`M${x - 9 * s} ${y} Q${x - 4 * s} ${y - 7 * s} ${x} ${y} Q${x + 4 * s} ${y - 7 * s} ${x + 9 * s} ${y}`}
      fill="none"
      stroke="#2a4a35"
      strokeWidth={1.6 * s}
      strokeLinecap="round"
    />
  );
}

function Stall({ x, y, s = 1, a = '#d93a2b', b = '#fff7e6' }: { x: number; y: number; s?: number; a?: string; b?: string }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <rect x="2" y="22" width="3" height="26" fill="#5a3b24" />
      <rect x="55" y="22" width="3" height="26" fill="#5a3b24" />
      {[0, 1, 2, 3, 4].map((i) => (
        <path key={i} d={`M${-4 + i * 13.6} 22 L${4 + i * 10.4} 6 L${9.2 + i * 10.4} 6 L${9.6 + i * 13.6} 22Z`} fill={i % 2 ? b : a} />
      ))}
      <rect x="4" y="38" width="52" height="10" rx="2" fill="#8a6240" />
      {[10, 22, 34, 46].map((cx, i) => (
        <circle key={cx} cx={cx} cy="36" r="5" fill={['#d93a2b', '#9b5fa8', '#b98a52', '#e8a020'][i]} />
      ))}
      <circle cx="30" cy="27" r="4" fill="#8a5a38" />
      <path d="M25 31 H35 L36 40 H24Z" fill="#fdf8ec" />
    </g>
  );
}

function Truck() {
  return (
    <svg width="190" height="92" viewBox="0 0 190 92" aria-hidden="true">
      <rect x="6" y="26" width="112" height="44" rx="5" fill="#d9a441" />
      <rect x="6" y="26" width="112" height="9" rx="4" fill="#b8801a" />
      {[18, 36, 54, 72, 90].map((cx, i) => (
        <circle key={cx} cx={cx + 4} cy="22" r="9" fill={['#d93a2b', '#9b5fa8', '#c18a4d', '#4aa85a', '#d93a2b'][i]} />
      ))}
      <path d="M118 36 H152 L170 56 V70 H118Z" fill="#1b7a3e" />
      <path d="M126 41 H150 L162 55 H126Z" fill="#cfe9f5" />
      <rect x="4" y="68" width="170" height="8" rx="3" fill="#3a2a1c" />
      {[34, 140].map((cx) => (
        <g key={cx} className="farm-wheel" style={{ transformOrigin: `${cx}px 78px` }}>
          <circle cx={cx} cy="78" r="13" fill="#1c1c1c" />
          <circle cx={cx} cy="78" r="5.5" fill="#c8f04c" />
          <path d={`M${cx} 66 V90 M${cx - 12} 78 H${cx + 12}`} stroke="#555" strokeWidth="2" />
        </g>
      ))}
    </svg>
  );
}

export default function FarmBackdrop() {
  const pathname = usePathname();
  if (!isFarmRoute(pathname)) return null;

  return (
    <div className="farm-backdrop" aria-hidden="true">
      <div className="farm-backdrop-sky" />
      <div className="farm-backdrop-sun">
        <span className="farm-backdrop-rays" />
      </div>

      {CLOUDS.map((c, i) => (
        <span key={i} className="farm-cloud" style={{ top: c.top, opacity: c.op, animationDuration: c.dur, animationDelay: c.delay }}>
          <Cloud w={c.w} />
        </span>
      ))}

      <svg className="farm-birds" viewBox="0 0 200 60" width="200" height="60">
        <Bird x={20} y={30} s={1.2} d="0s" />
        <Bird x={52} y={18} s={1} d="-0.3s" />
        <Bird x={80} y={34} s={1.1} d="-0.6s" />
        <Bird x={112} y={22} s={0.9} d="-0.2s" />
        <Bird x={146} y={36} s={1} d="-0.5s" />
      </svg>

      {MOTES.map((m, i) => (
        <span key={i} className="farm-mote" style={{ left: m.left, width: m.size, height: m.size, animationDuration: m.dur, animationDelay: m.delay }} />
      ))}
      {LEAVES.map((l, i) => (
        <span key={i} className="farm-bleaf" style={{ left: l.left, animationDuration: l.dur, animationDelay: l.delay }}>
          <svg width={l.s} height={l.s} viewBox="0 0 24 24">
            <path d="M4 20C4 9 11 4 21 3c0 10-5 17-14 17-1 0-2 0-3 0z" fill="#3d9a57" opacity="0.6" />
            <path d="M5 19C9 14 13 10 18 6" stroke="#135c2e" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          </svg>
        </span>
      ))}

      {pathname !== '/' &&
        FRAMES.map((f) => (
          <figure
            key={f.photo}
            className={`farm-sideframe ${f.side === 'l' ? 'farm-sideframe-l' : 'farm-sideframe-r'} ${pathname.startsWith('/tools') || pathname.startsWith('/prices') ?'farm-sideframe-wide' : ''}`}
            style={{ top: f.top, ['--rot' as string]: `${f.rot}deg`, animationDelay: f.delay }}
          >
            <span className="farm-sideframe-img" style={{ backgroundImage: `url(/photos/${f.photo}.jpg)` }} />
            <span className="farm-sidesticker farm-float" style={{ animationDelay: f.delay }}>
              <ProduceIcon name={f.sticker} px={54} />
            </span>
          </figure>
        ))}

      <svg className="farm-backdrop-land" viewBox="0 0 1440 320" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="fb-h1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#d6e8b8" />
            <stop offset="1" stopColor="#c3dd9f" />
          </linearGradient>
          <linearGradient id="fb-h2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#a9d082" />
            <stop offset="1" stopColor="#8cbd66" />
          </linearGradient>
        </defs>
        <path d="M0 150 C200 90 380 140 600 112 C820 84 1040 150 1240 110 C1340 92 1400 100 1440 108 V320 H0Z" fill="url(#fb-h1)" />
        <Stall x={170} y={118} s={0.8} />
        <Stall x={262} y={124} s={0.7} a="#e8a020" />
        <Stall x={1090} y={110} s={0.8} a="#1b7a3e" />
        <Stall x={1190} y={106} s={0.7} b="#fdf1dc" />
        <path d="M0 196 C240 150 440 200 700 176 C940 154 1160 206 1440 168 V320 H0Z" fill="url(#fb-h2)" />
        <g className="farm-sway-slow">
          {Array.from({ length: 4 }, (_, row) => (
            <g key={row} opacity={0.5 + row * 0.12}>
              {Array.from({ length: 56 }, (_, i) => {
                const x = (i + row * 0.45) * (1440 / 55) - 12;
                const y = 226 + row * 19;
                const s = 0.9 + row * 0.2;
                return (
                  <path
                    key={i}
                    d={`M${x} ${y} q ${-6 * s} ${-15 * s} 0 ${-26 * s} q ${6 * s} ${10 * s} 0 ${26 * s}z`}
                    fill={row % 2 ? '#2f8a4c' : '#1b7a3e'}
                  />
                );
              })}
            </g>
          ))}
        </g>
        <path d="M0 300 C300 288 700 306 1440 292 V320 H0Z" fill="#6f4d31" opacity="0.85" />
      </svg>

      <div className="farm-truck">
        <Truck />
      </div>
    </div>
  );
}
