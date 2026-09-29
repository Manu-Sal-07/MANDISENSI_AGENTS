'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, WifiOff } from 'lucide-react';

import { mandiApi } from '@/services/api';
import ProduceIcon, { resolveProduce } from './ProduceIcon';
import { CALL_VISUAL, normaliseCall } from './CallCard';

/**
 * Mandis within reach, and what each is calling today.
 *
 * Rows rather than cards. A farmer is comparing four or five markets to
 * decide where to take a load, and comparison wants a single scannable
 * column — equal-sized cards in a grid make the eye travel in two
 * directions to do one job.
 */

interface Opportunity {
  id: string;
  mandi_name: string;
  hot_commodity: string;
  decision: string;
  reasoning?: string;
  price_change_pct: number;
  confidence: number;
  risk_level: string;
}

export default function NearbyMandis() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['discovery-feed', 'bengaluru'],
    queryFn: () => mandiApi.getDiscoveryFeed('bengaluru'),
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="farm-row h-24 animate-pulse bg-white/70" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="farm-card flex items-start gap-3 p-6">
        <WifiOff className="mt-0.5 h-5 w-5 shrink-0 text-[var(--farm-ink-faint)]" />
        <div>
          <p className="text-base font-semibold text-[var(--farm-ink)]">
            No connection to the mandi records.
          </p>
          <p className="mt-1 text-sm text-[var(--farm-ink-soft)]">
            Check your network and pull to refresh.
          </p>
        </div>
      </div>
    );
  }

  const feed = (data as Opportunity[]) ?? [];

  if (!feed.length) {
    return (
      <div className="farm-card p-6">
        <p className="text-base font-semibold text-[var(--farm-ink)]">
          No mandis reporting near you today.
        </p>
        <p className="mt-1 text-sm text-[var(--farm-ink-soft)]">
          Markets close on holidays. Try again tomorrow morning.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {feed.map((item) => {
        const call = normaliseCall(item.decision);
        const visual = CALL_VISUAL[call];
        const produce = resolveProduce(item.hot_commodity);
        const rising = item.price_change_pct > 0;

        return (
          <li key={item.id}>
            <Link
              href={`/mandi/${item.id}`}
              className="farm-row farm-focus flex items-center gap-3 p-4 sm:gap-4"
            >
              {/* One icon, sized by CSS. Rendering two and hiding one by
                  breakpoint collided with the component's own `inline-flex`
                  and showed both. */}
              <ProduceIcon name={item.hot_commodity} size="md" />

              <div className="min-w-0 flex-1">
                {/* The mandi name identifies the row, so it wraps rather
                    than truncating to "Bang…". `break-words` is what stops
                    a long single token like "Yeshwanthpur" overflowing its
                    column and running under the verb. */}
                <p className="break-words text-base font-bold leading-tight text-[var(--farm-ink)]">
                  {item.mandi_name}
                </p>
                <p className="mt-0.5 text-sm text-[var(--farm-ink-soft)]">
                  {produce.label} · {rising ? 'up' : 'down'}{' '}
                  {Math.abs(item.price_change_pct).toFixed(1)}%
                </p>
              </div>

              <div className="shrink-0 text-right">
                <span
                  className="farm-display inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-sm leading-tight sm:text-base"
                  style={{ background: visual.wash, color: visual.colour }}
                >
                  {visual.verbShort}
                </span>
                <span
                  className="mt-1 block text-xs text-[var(--farm-ink-faint)]"
                  lang="hi"
                >
                  {visual.hindiShort}
                </span>
              </div>

              <ChevronRight className="h-5 w-5 shrink-0 text-[var(--farm-ink-faint)]" />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
