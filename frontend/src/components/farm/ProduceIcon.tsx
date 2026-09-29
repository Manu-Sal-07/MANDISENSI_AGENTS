import React from 'react';

/**
 * Drawn produce for the farmer surface.
 *
 * The trader views identify a commodity by a three-letter ticker code
 * (`TOM`, `ONI`) in the spirit of an exchange symbol. That is the right
 * call there and the wrong one here: a farmer scanning a list in sunlight
 * recognises the shape and colour of a tomato instantly and has to stop and
 * read `TOM`. These are simple enough to read at 32px on a low-density
 * screen and still hold up at 96px in the hero.
 *
 * Each shape is a handful of paths, so the whole set costs less than a
 * single photograph on a rural connection.
 */

export type ProduceName =
  | 'tomato'
  | 'onion'
  | 'potato'
  | 'garlic'
  | 'ginger'
  | 'dry_chillies';

interface ProduceVisual {
  label: string;
  /** Devanagari name — the audience reads this faster than the English. */
  hindi: string;
  tint: string;
  draw: React.ReactNode;
}

const LEAF = '#1b7a3e';
const LEAF_DEEP = '#135c2e';

const PRODUCE: Record<ProduceName, ProduceVisual> = {
  tomato: {
    label: 'Tomato',
    hindi: 'टमाटर',
    tint: '#d93a2b',
    draw: (
      <>
        <circle cx="32" cy="37" r="21" fill="#e04b36" />
        <path d="M32 16c9 2 16 9 19 18-6-3-13-4-19-4s-13 1-19 4c3-9 10-16 19-18z" fill="#f2684f" opacity=".55" />
        <path d="M24 18c3 2 5 3 8 3s5-1 8-3c-1 3-4 5-8 5s-7-2-8-5z" fill={LEAF_DEEP} />
        <path d="M32 11c1 0 2 1 2 3v4h-4v-4c0-2 1-3 2-3z" fill={LEAF_DEEP} />
        <path d="M32 17c-5 0-9-2-13-5 5-1 9 0 13 2 4-2 8-3 13-2-4 3-8 5-13 5z" fill={LEAF} />
      </>
    ),
  },
  onion: {
    label: 'Onion',
    hindi: 'प्याज़',
    tint: '#9b5fa8',
    draw: (
      <>
        <path d="M32 58c-11 0-19-8-19-18 0-9 7-17 19-24 12 7 19 15 19 24 0 10-8 18-19 18z" fill="#b978c4" />
        <path d="M32 58c-4 0-7-8-7-18 0-9 3-17 7-24 4 7 7 15 7 24 0 10-3 18-7 18z" fill="#cf95d8" opacity=".7" />
        <path d="M32 16v-6M32 12c-2-3-5-4-8-4 1 3 4 5 8 4zM32 12c2-3 5-4 8-4-1 3-4 5-8 4z" stroke={LEAF} strokeWidth="2.5" strokeLinecap="round" fill="none" />
      </>
    ),
  },
  potato: {
    label: 'Potato',
    hindi: 'आलू',
    tint: '#a8763f',
    draw: (
      <>
        <path d="M14 34c0-11 9-19 21-19s17 6 17 15c0 12-10 22-22 22S14 45 14 34z" fill="#c08d54" />
        <path d="M20 28c4-6 11-9 18-8-5 1-10 4-13 8-2 3-5 3-5 0z" fill="#d6a573" opacity=".7" />
        <ellipse cx="26" cy="33" rx="2.4" ry="1.7" fill="#8a6240" opacity=".65" />
        <ellipse cx="38" cy="28" rx="2" ry="1.4" fill="#8a6240" opacity=".55" />
        <ellipse cx="36" cy="43" rx="2.2" ry="1.6" fill="#8a6240" opacity=".6" />
      </>
    ),
  },
  garlic: {
    label: 'Garlic',
    hindi: 'लहसुन',
    tint: '#8d8a7e',
    draw: (
      <>
        <path d="M32 57c-10 0-17-7-17-16 0-8 5-14 10-20 2-2 5-4 7-4s5 2 7 4c5 6 10 12 10 20 0 9-7 16-17 16z" fill="#efeade" />
        <path d="M32 57c-4 0-6-7-6-16 0-8 2-15 6-21 4 6 6 13 6 21 0 9-2 16-6 16z" fill="#fffdf6" />
        <path d="M22 26c-2 6-3 11-3 15M42 26c2 6 3 11 3 15" stroke="#cfc8b6" strokeWidth="1.6" strokeLinecap="round" fill="none" />
        <path d="M32 17v-7" stroke={LEAF_DEEP} strokeWidth="2.6" strokeLinecap="round" />
      </>
    ),
  },
  ginger: {
    label: 'Ginger',
    hindi: 'अदरक',
    tint: '#c8922f',
    draw: (
      <>
        <path d="M17 38c0-8 6-13 13-13 4 0 6 2 9 2 5 0 9 3 9 9 0 8-7 14-16 14-9 0-15-5-15-12z" fill="#d9a44e" />
        <path d="M30 25c-1-5 2-9 6-9 3 0 5 2 5 5s-3 5-6 5c-2 0-4 0-5-1z" fill="#c8922f" />
        <path d="M45 34c5-1 8 2 8 6s-3 6-7 5" fill="#c8922f" />
        <path d="M24 34c4-2 9-2 13 0M26 43c4-2 9-2 13 0" stroke="#a87a2c" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity=".8" />
      </>
    ),
  },
  dry_chillies: {
    label: 'Chilli',
    hindi: 'मिर्च',
    tint: '#c02a1f',
    draw: (
      <>
        <path d="M38 13c2 8 4 16 2 25-2 10-8 17-16 19-3 1-5-2-3-5 6-7 9-14 10-23 1-7 2-12 3-16 1-2 3-2 4 0z" fill="#cf3226" />
        <path d="M38 18c1 7 2 14 0 21-2 8-6 14-11 17 5-7 8-14 9-22 1-6 1-11 2-16z" fill="#e5534a" opacity=".6" />
        <path d="M36 13c-3-3-7-4-11-3 2 3 5 5 9 5" fill={LEAF} />
        <path d="M37 12V8" stroke={LEAF_DEEP} strokeWidth="2.4" strokeLinecap="round" />
      </>
    ),
  },
};

/** Falls back to a generic crate rather than showing nothing. */
const FALLBACK: ProduceVisual = {
  label: 'Produce',
  hindi: 'फ़सल',
  tint: '#8a6240',
  draw: (
    <>
      <path d="M12 26h40l-4 28H16z" fill="#c08d54" />
      <path d="M12 26h40v6H12z" fill="#a8763f" />
      <path d="M22 32v20M32 32v20M42 32v20" stroke="#8a6240" strokeWidth="1.6" opacity=".5" />
    </>
  ),
};

export function resolveProduce(name: string): ProduceVisual {
  const key = (name || '').toLowerCase().replace(/[\s-]+/g, '_');
  const direct = PRODUCE[key as ProduceName];
  if (direct) return direct;
  const partial = (Object.keys(PRODUCE) as ProduceName[]).find(
    (k) => key.includes(k) || k.includes(key)
  );
  return partial ? PRODUCE[partial] : FALLBACK;
}

const SIZES = { sm: 36, md: 52, lg: 72, xl: 104 } as const;

interface ProduceIconProps {
  name: string;
  size?: keyof typeof SIZES;
  /** Exact pixel size, overriding the `size` step. Used by the drifting
      scene, where each crate needs its own scale to read as depth. */
  px?: number;
  /** Tinted circular backing. Off for the hero, where the shape stands alone. */
  plated?: boolean;
  className?: string;
  sway?: boolean;
}

export default function ProduceIcon({
  name,
  size = 'md',
  px: pxOverride,
  plated = true,
  className = '',
  sway = false,
}: ProduceIconProps) {
  const produce = resolveProduce(name);
  const px = pxOverride ?? SIZES[size];
  const art = (
    <svg
      viewBox="0 0 64 64"
      width={plated ? px * 0.68 : px}
      height={plated ? px * 0.68 : px}
      role="img"
      aria-label={produce.label}
      className={sway ? 'farm-sway' : undefined}
    >
      {produce.draw}
    </svg>
  );

  if (!plated) return <span className={className}>{art}</span>;

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full ${className}`}
      style={{
        width: px,
        height: px,
        background: `color-mix(in srgb, ${produce.tint} 12%, #ffffff)`,
        border: `1px solid color-mix(in srgb, ${produce.tint} 24%, transparent)`,
      }}
    >
      {art}
    </span>
  );
}
