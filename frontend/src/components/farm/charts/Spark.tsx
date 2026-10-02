'use client';

import React from 'react';

/** A crop's last month as a single line: shape only, no axes. Direction is
 *  never carried by colour alone — a signed number always sits beside it. */
export default function Spark({
  values,
  width = 88,
  height = 28,
  colour = 'var(--farm-ink-soft)',
}: {
  values: number[];
  width?: number;
  height?: number;
  colour?: string;
}) {
  if (values.length < 2) return <svg width={width} height={height} aria-hidden="true" />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 3;
  const points = values.map((v, i) => [
    pad + (i / (values.length - 1)) * (width - pad * 2),
    height - pad - ((v - min) / span) * (height - pad * 2),
  ]);
  const d = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const [lx, ly] = points[points.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={d} fill="none" stroke={colour} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly} r={3} fill={colour} stroke="var(--farm-paper)" strokeWidth={2} />
    </svg>
  );
}
