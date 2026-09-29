'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { mandiApi } from '@/services/api';
import ProduceIcon, { resolveProduce } from './ProduceIcon';
import { CALL_VISUAL, resolveCall } from './CallCard';

/**
 * Every crop's call for today, in one glance.
 *
 * Laid out as a horizontal, swipeable strip rather than a grid. A grid
 * needs a column count decided in advance, and five crops against two or
 * three columns always leaves an orphaned tile in the last row with dead
 * space beside it — exactly the "broken into pieces" look this page was
 * criticised for. A strip has no such constraint: it holds five crops or
 * fifteen with the same rhythm, and swiping a row of produce is the
 * gesture a farmer already uses on a ticker or a photo reel.
 *
 * Each tile also carries a wash of its own decision colour rather than
 * sitting on plain white with only a hairline strip — the colour is the
 * fastest-read signal on the page, so it earns more than a sliver.
 */

interface Decision {
  commodity: string;
  decision: string;
  /** Which of the three outcomes produced `decision`. See CallCard. */
  call_type?: string | null;
  /** Why the forecast is absent, when it is. */
  reason?: string | null;
  price_change_pct: number;
}

export default function TodaysCalls() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['quick-decisions', 'bengaluru'],
    queryFn: () => mandiApi.getQuickDecisions('bengaluru'),
    staleTime: 1000 * 60 * 2,
  });

  if (isLoading) {
    return (
      <div className="farm-scroll-x no-scrollbar">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="farm-row h-32 w-[8.75rem] shrink-0 animate-pulse bg-white/70 sm:w-[9.75rem]"
          />
        ))}
      </div>
    );
  }

  const decisions: Decision[] = (data as { decisions?: Decision[] })?.decisions ?? [];

  if (isError || !decisions.length) {
    return (
      <div className="farm-card p-6 text-center">
        <p className="text-base font-semibold text-[var(--farm-ink)]">
          Today&rsquo;s calls are not in yet.
        </p>
        <p className="mt-1 text-sm text-[var(--farm-ink-soft)]">
          Mandi records usually arrive by the afternoon. Check back later.
        </p>
      </div>
    );
  }

  return (
    <ul className="farm-scroll-x no-scrollbar" role="list">
      {decisions.map((item) => {
        const call = resolveCall(item);
        const visual = CALL_VISUAL[call];
        const produce = resolveProduce(item.commodity);
        const rising = item.price_change_pct > 0;
        // With no forecast there is no expected move. The backend sends 0.0
        // as a placeholder, and drawing it as "▼ 0.0%" told the farmer the
        // price was flat -- a measurement we never made.
        const unknown = call === 'UNKNOWN';

        return (
          <li
            key={item.commodity}
            className="farm-row w-[8.75rem] shrink-0 overflow-hidden sm:w-[9.75rem]"
          >
            <div className="h-1.5 w-full" style={{ background: visual.colour }} />
            <div
              className="flex flex-col items-start gap-2.5 p-3.5"
              style={{ background: `color-mix(in oklch, ${visual.colour} 7%, transparent)` }}
            >
              <ProduceIcon name={item.commodity} size="md" />
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-[var(--farm-ink)]">
                  {produce.label}
                </p>
                <p
                  className="farm-display text-lg leading-tight"
                  style={{ color: visual.colour }}
                >
                  {visual.verbShort}
                </p>
                {unknown ? (
                  <p className="text-xs font-medium text-[var(--farm-ink-faint)]">
                    Not enough records
                  </p>
                ) : (
                  <p className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                    {rising ? '▲' : '▼'} {Math.abs(item.price_change_pct).toFixed(1)}%
                  </p>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
