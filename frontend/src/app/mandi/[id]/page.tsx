'use client';

/**
 * One mandi, every crop.
 *
 * The farmer arrived here from a row on the home page, so the question has
 * narrowed: they are considering taking a load to this market and want to
 * know which of their crops it is paying for today.
 *
 * Crops are listed, not gridded. A grid of equal cards asks the eye to
 * travel in two directions to do one job; a single column of rows sorted
 * loudest-first puts the best reason to make the trip at the top.
 */

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ChevronLeft, Loader2, Truck, WifiOff } from 'lucide-react';

import { mandiApi } from '@/services/api';
import ProduceIcon, { resolveProduce } from '@/components/farm/ProduceIcon';
import {
  CALL_VISUAL,
  resolveCall,
  tidyNote,
  type Call,
} from '@/components/farm/CallCard';
import FarmScene from '@/components/farm/FarmScene';

interface CommodityDetail {
  name: string;
  decision: string;
  /** Which of the three outcomes produced `decision`. See CallCard. */
  call_type?: string | null;
  /** Why there is no forecast, when there is none. */
  reason?: string | null;
  reasoning?: string;
  price_change: number;
  price: number;
  confidence: number;
}

// Sell is the most time-critical instruction, so it leads; wait is the
// least, so it trails. Sorting by urgency rather than alphabetically means
// the row that needs acting on today is the first one seen.
// UNKNOWN trails everything: a crop we have no reading for is the last
// thing a farmer needs to look at, and floating it above a real SELL would
// be the ranking equivalent of the bug this taxonomy fixes.
const CALL_URGENCY: Record<Call, number> = { SELL: 0, HOLD: 1, WAIT: 2, UNKNOWN: 3 };

const formatRupees = (value?: number | null) =>
  value == null || Number.isNaN(value)
    ? '—'
    : `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;

export default function MandiDetailPage() {
  const params = useParams();
  const router = useRouter();
  const mandiId = params.id as string;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['mandi-details', mandiId],
    queryFn: () => mandiApi.getDiscoveryDetails(mandiId),
    enabled: !!mandiId,
  });

  if (isLoading) {
    return (
      <div className="farm-surface flex min-h-screen flex-col items-center justify-center gap-4">
        <Loader2 className="h-9 w-9 animate-spin" style={{ color: 'var(--leaf)' }} />
        <p className="text-base font-semibold text-[var(--farm-ink-soft)]">
          Checking today&rsquo;s prices…
        </p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="farm-surface flex min-h-screen items-center justify-center px-6">
        <div className="farm-card max-w-sm p-8 text-center">
          <WifiOff className="mx-auto h-10 w-10 text-[var(--farm-ink-faint)]" />
          <h2 className="farm-display mt-4 text-2xl text-[var(--farm-ink)]">
            No connection
          </h2>
          <p className="mt-2 text-base text-[var(--farm-ink-soft)]">
            The mandi records could not be reached. Check your network, then
            try again.
          </p>
          <button
            onClick={() => refetch()}
            className="farm-focus farm-tap mt-6 w-full rounded-2xl text-base font-bold text-white"
            style={{ background: 'var(--leaf)' }}
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const commodities: CommodityDetail[] = [...(data?.commodities ?? [])].sort(
    (a, b) =>
      CALL_URGENCY[resolveCall(a)] -
      CALL_URGENCY[resolveCall(b)]
  );

  const sellCount = commodities.filter(
    (c) => resolveCall(c) === 'SELL'
  ).length;

  return (
    <div className="farm-surface relative min-h-screen pb-28 md:pb-16">
      {/* A shallow band of the same field as the home page — enough to
          place the page, not so much that it competes with five rows of
          prices. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 overflow-hidden">
        <FarmScene />
      </div>

      <div className="relative mx-auto max-w-3xl px-4 pt-6 lg:max-w-5xl">
        <button
          onClick={() => router.back()}
          className="farm-focus -ml-2 flex items-center gap-1.5 rounded-lg px-2 py-2 text-base font-semibold text-[var(--farm-ink-soft)] transition-colors hover:text-[var(--farm-ink)]"
        >
          <ChevronLeft className="h-5 w-5" />
          Back
        </button>

        <header className="mt-3">
          <h1 className="farm-display text-4xl leading-tight text-[var(--farm-ink)] sm:text-5xl">
            {data?.mandi_name}
          </h1>
          <p className="mt-1.5 text-base text-[var(--farm-ink-soft)]">
            {sellCount > 0
              ? `${sellCount} ${sellCount === 1 ? 'crop is' : 'crops are'} worth selling here today.`
              : 'Nothing urgent here today — prices are steady.'}
          </p>
        </header>

        {/* ── Crops ─────────────────────────────────────────────── */}
        <ul className="farm-section mt-7 space-y-3">
          {commodities.map((comm, index) => {
            const call = resolveCall(comm);
            const visual = CALL_VISUAL[call];
            const produce = resolveProduce(comm.name);
            const rising = comm.price_change > 0;
            // Price, weekly move and confidence are all placeholder zeros
            // when no forecast exists. Rendering them drew a ₹0 crop sitting
            // flat at 0.0% with zero confidence dots -- three fabricated
            // measurements presented with the same furniture as real ones.
            const unknown = call === 'UNKNOWN';

            return (
              <motion.li
                key={comm.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05, duration: 0.35 }}
                className="farm-row overflow-hidden"
              >
                <div className="flex">
                  <div className="w-1.5 shrink-0" style={{ background: visual.colour }} />

                  <div className="min-w-0 flex-1 p-4 sm:p-5">
                    <div className="flex items-start gap-4">
                      <ProduceIcon name={comm.name} size="lg" />

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-x-3">
                          <h3 className="text-lg font-bold text-[var(--farm-ink)]">
                            {produce.label}
                          </h3>
                          <span
                            className="farm-display text-base text-[var(--farm-ink-faint)]"
                            lang="hi"
                          >
                            {produce.hindi}
                          </span>
                        </div>

                        <p
                          className="farm-display text-2xl leading-tight"
                          style={{ color: visual.colour }}
                        >
                          {visual.verb}
                        </p>

                        {/* Same filter as the hero card: the engine's raw
                            sentence prints the mandi slug and the figure
                            already shown below it, so only a well-formed
                            reason survives. */}
                        <p className="mt-1.5 max-w-[52ch] text-sm leading-relaxed text-[var(--farm-ink-soft)]">
                          {unknown
                            ? comm.reason || visual.plain
                            : tidyNote(comm.reasoning, visual.plain)}
                        </p>
                      </div>
                    </div>

                    {unknown ? (
                      <p className="mt-4 border-t border-[var(--farm-line)] pt-3.5 text-sm font-medium text-[var(--farm-ink-faint)]">
                        No price, expected move or confidence is shown for this
                        crop, because none was calculated.
                      </p>
                    ) : (
                    <dl className="mt-4 flex flex-wrap gap-x-7 gap-y-3 border-t border-[var(--farm-line)] pt-3.5">
                      <div>
                        <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                          Price per quintal
                        </dt>
                        <dd className="farm-display text-xl text-[var(--farm-ink)]">
                          {formatRupees(comm.price)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                          This week
                        </dt>
                        <dd
                          className="farm-display text-xl"
                          style={{ color: visual.colour }}
                        >
                          {rising ? '▲' : '▼'} {Math.abs(comm.price_change).toFixed(1)}%
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold text-[var(--farm-ink-faint)]">
                          How sure
                        </dt>
                        <dd className="flex items-center gap-1.5 pt-2">
                          {[0, 1, 2, 3].map((i) => (
                            <span
                              key={i}
                              className="block h-2.5 w-5 rounded-full"
                              style={{
                                background:
                                  i < Math.round((comm.confidence || 0) * 4)
                                    ? visual.colour
                                    : 'var(--farm-line)',
                              }}
                            />
                          ))}
                        </dd>
                      </div>
                    </dl>
                    )}
                  </div>
                </div>
              </motion.li>
            );
          })}
        </ul>

        {/* ── Getting there ─────────────────────────────────────── */}
        <div
          className="farm-card mt-8 flex items-start gap-4 p-5 sm:p-6"
          style={{ background: 'var(--farm-paper-warm)' }}
        >
          <span
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
            style={{ background: 'var(--turmeric-wash)' }}
          >
            <Truck className="h-6 w-6" style={{ color: 'var(--turmeric)' }} />
          </span>
          <div>
            <h3 className="farm-display text-xl text-[var(--farm-ink)]">
              Getting your load there
            </h3>
            <p className="mt-1.5 max-w-[56ch] text-base leading-relaxed text-[var(--farm-ink-soft)]">
              {data?.transport_suggestion ||
                'Leave early. Produce that travels in the cool of the morning arrives fresher and grades better.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
