'use client';

import Link from 'next/link';
import { MapPin, Loader2 } from 'lucide-react';

import { useLocation } from '@/hooks/useLocation';
import { useAppStore } from '@/store/useAppStore';

/**
 * Header for the farmer surface.
 *
 * The trader header carries brand, a product nav and a theme switch. None
 * of that helps here: there is one place to go, and the only piece of
 * state a farmer needs at the top of the screen is *which mandi am I
 * seeing prices for*, because every number below depends on it.
 *
 * So the location is the header. It is also the one control, sized as a
 * real button rather than a bracketed link, because it is tapped with a
 * thumb outdoors.
 */
export default function FarmHeader() {
  const { requestLocation } = useLocation();
  const { personalizationStatus, viewMode, resetToDefault } = useAppStore();

  const isRequesting = personalizationStatus === 'requesting';
  const isPersonalized = viewMode === 'personalized';

  return (
    <header
      className="sticky top-0 z-50 border-b border-[var(--farm-line)]"
      style={{ background: 'rgba(251, 253, 246, 0.92)', backdropFilter: 'blur(12px)' }}
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 lg:max-w-5xl">
        <Link href="/" className="farm-focus flex min-w-0 items-center gap-3 rounded-xl">
          <span
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
            style={{ background: 'var(--leaf-wash)' }}
          >
            <MapPin className="h-5 w-5" style={{ color: 'var(--leaf)' }} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-base font-bold leading-tight text-[var(--farm-ink)]">
              {isPersonalized ? 'Mandis near you' : 'Bengaluru mandis'}
            </span>
            <span className="block truncate text-xs text-[var(--farm-ink-faint)]">
              Today&rsquo;s prices
            </span>
          </span>
        </Link>

        <button
          onClick={isPersonalized ? resetToDefault : requestLocation}
          disabled={isRequesting}
          className="farm-focus shrink-0 rounded-xl border border-[var(--farm-line)] bg-white px-3.5 py-2.5 text-sm font-bold text-[var(--leaf)] transition-colors hover:border-[var(--leaf)] disabled:opacity-50"
        >
          {isRequesting ? (
            <span className="flex items-center gap-1.5">
              <Loader2 className="h-4 w-4 animate-spin" />
              Finding
            </span>
          ) : isPersonalized ? (
            'Reset'
          ) : (
            'Use my location'
          )}
        </button>
      </div>
    </header>
  );
}
