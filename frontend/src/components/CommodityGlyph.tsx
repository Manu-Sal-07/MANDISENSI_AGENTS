import React from 'react';

/**
 * Compact ticker-style glyph for a commodity — three-letter code on a
 * tinted badge, in the spirit of a stock ticker symbol (AAPL, TSLA) rather
 * than a food-delivery emoji. Reads as professional at any density and
 * degrades gracefully for commodities outside the known set.
 */
const COMMODITY_STYLES: Record<string, { code: string; color: string }> = {
  tomato: { code: 'TOM', color: 'var(--bearish)' },
  onion: { code: 'ONI', color: 'var(--analytical)' },
  potato: { code: 'POT', color: 'var(--warning)' },
  garlic: { code: 'GAR', color: 'var(--bullish)' },
  ginger: { code: 'GIN', color: 'var(--intelligence)' },
  dry_chillies: { code: 'CHL', color: 'var(--bearish)' },
};

function resolve(name: string) {
  const key = name.toLowerCase().replace(/\s+/g, '_');
  const match = Object.entries(COMMODITY_STYLES).find(([k]) => key.includes(k));
  if (match) return match[1];
  return { code: name.slice(0, 3).toUpperCase(), color: 'var(--accent)' };
}

interface CommodityGlyphProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_MAP = {
  sm: 'h-9 w-9 text-[9px] rounded-xl',
  md: 'h-14 w-14 text-[11px] rounded-2xl',
  lg: 'h-16 w-16 text-xs rounded-2xl',
};

export default function CommodityGlyph({ name, size = 'md', className = '' }: CommodityGlyphProps) {
  const { code, color } = resolve(name);
  return (
    <div
      className={`flex shrink-0 items-center justify-center font-mono font-bold tracking-wide transition-transform group-hover:scale-105 ${SIZE_MAP[size]} ${className}`}
      style={{
        color,
        background: `color-mix(in oklch, ${color} 14%, var(--surface-2))`,
        border: `1px solid color-mix(in oklch, ${color} 22%, transparent)`,
      }}
    >
      {code}
    </div>
  );
}
