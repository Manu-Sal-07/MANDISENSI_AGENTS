'use client';

import React from 'react';
import ProduceIcon, { type ProduceName } from './ProduceIcon';

/**
 * The ambient field behind the farmer hero.
 *
 * Built from SVG and CSS rather than photography. That is a bandwidth
 * decision before it is an aesthetic one — this scene is a few kilobytes
 * where a usable hero photograph is several megabytes, and the people
 * using this are often on a metered rural connection. It also means the
 * scene inherits the palette instead of fighting it.
 *
 * It is deliberately slow. Produce drifts past over ninety seconds and the
 * sun breathes over fourteen; at that pace it reads as weather rather than
 * as an animation asking to be watched. The decision in front of it stays
 * the only thing moving fast enough to notice.
 */

interface Drifter {
  name: ProduceName;
  /** vertical position as a percentage of the scene height */
  top: number;
  size: number;
  /** seconds for one full pass */
  duration: number;
  delay: number;
  opacity: number;
}

// Staggered so no two crates cross at the same height or the same moment.
const DRIFTERS: Drifter[] = [
  { name: 'tomato', top: 18, size: 64, duration: 82, delay: 0, opacity: 0.62 },
  { name: 'onion', top: 54, size: 54, duration: 104, delay: -22, opacity: 0.52 },
  { name: 'potato', top: 72, size: 70, duration: 94, delay: -55, opacity: 0.55 },
  { name: 'dry_chillies', top: 34, size: 48, duration: 118, delay: -74, opacity: 0.48 },
  { name: 'garlic', top: 62, size: 44, duration: 136, delay: -12, opacity: 0.44 },
  { name: 'ginger', top: 26, size: 58, duration: 110, delay: -90, opacity: 0.46 },
];

export default function FarmScene({ className = '' }: { className?: string }) {
  return (
    <div className={`farm-scene ${className}`} aria-hidden="true">
      <div className="farm-sun" />

      {/* Fields. Three bands of decreasing distance, the furthest palest,
          so the scene has depth without needing detail. */}
      <svg
        className="absolute inset-x-0 bottom-0 w-full"
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
        style={{ height: '70%' }}
      >
        <path
          d="M0 186c180-30 320 18 520 8s330-52 520-36 300 44 400 34v128H0z"
          fill="#cfe6b4"
        />
        <path
          d="M0 232c210-26 350 14 560 6s340-40 540-24 260 34 340 28v78H0z"
          fill="#b2d894"
        />
        <path
          d="M0 274c230-18 380 12 620 6s360-26 560-14 200 18 260 14v40H0z"
          fill="#8fc46c"
        />

        {/* Furrows, converging slightly to suggest a ploughed field
            receding rather than a flat green band. */}
        <g stroke="#79b257" strokeWidth="2" opacity=".55">
          {Array.from({ length: 14 }).map((_, i) => {
            const x = i * 110 - 60;
            return <path key={i} d={`M${x} 320 L${x + 46} 268`} />;
          })}
        </g>
      </svg>

      {/* Produce drifting across, like crates going past on a cart. */}
      {DRIFTERS.map((d) => (
        <div
          key={d.name}
          className="farm-drift"
          style={{
            top: `${d.top}%`,
            opacity: d.opacity,
            animationDuration: `${d.duration}s`,
            animationDelay: `${d.delay}s`,
          }}
        >
          <ProduceIcon name={d.name} plated={false} px={d.size} className="block" />
        </div>
      ))}

      {/* A soft wash at the foot of the scene so text sitting over the
          fields keeps its contrast rather than relying on luck. */}
      <div
        className="absolute inset-x-0 bottom-0 h-1/2"
        style={{
          background:
            'linear-gradient(to top, rgba(251,253,246,0.86) 0%, rgba(251,253,246,0.3) 52%, transparent 100%)',
        }}
      />
    </div>
  );
}
