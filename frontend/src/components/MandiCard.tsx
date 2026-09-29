'use client';

import React from 'react';
import { ChevronRight, Zap, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import CommodityGlyph from './CommodityGlyph';

interface MandiCardProps {
  opportunity: {
    id: string;
    mandi_name: string;
    hot_commodity: string;
    decision: 'SELL' | 'HOLD' | 'WAIT';
    reasoning?: string;
    price_change_pct: number;
    confidence: number;
    risk_level: string;
  };
}

const DECISION_STYLE: Record<string, string> = {
  SELL: 'text-bearish',
  HOLD: 'text-bullish',
  WAIT: 'text-warning',
};

export default function MandiCard({ opportunity }: MandiCardProps) {
  const getConfidenceText = (conf: number) => {
    if (conf > 0.8) return 'High confidence';
    if (conf > 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  const positive = opportunity.price_change_pct > 0;

  return (
    <Link href={`/mandi/${opportunity.id}`} className="group block">
      <div className="floating-card floating-card-hover elite-card rounded-3xl p-7 sm:p-8">
        {/* Header */}
        <div className="mb-7 flex items-start justify-between">
          <div className="flex items-center gap-4">
            <CommodityGlyph name={opportunity.hot_commodity} size="md" />
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <span className="live-dot" />
                <span className="label-caps text-[9.5px]">{opportunity.mandi_name.toUpperCase()}</span>
              </div>
              <h3 className="font-display text-2xl font-bold tracking-tight text-foreground">
                {opportunity.hot_commodity}
              </h3>
            </div>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border text-neutral-signal transition-all group-hover:border-accent/40 group-hover:bg-accent/10 group-hover:text-accent-strong">
            <ChevronRight className="h-5 w-5" />
          </div>
        </div>

        {/* Decision */}
        <div className="flex items-end justify-between gap-4 border-b border-border pb-7">
          <div className="space-y-1.5">
            <div className={`font-display text-5xl font-bold tracking-tight sm:text-6xl ${DECISION_STYLE[opportunity.decision] || 'text-neutral-signal'}`}>
              {opportunity.decision}
            </div>
            <p className="line-clamp-1 max-w-[220px] text-sm font-medium italic text-neutral-signal">
              {opportunity.reasoning || 'Analyzing market signals…'}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <span className="label-caps text-[9.5px]">Trust Score</span>
            <p className="mt-1 flex items-center justify-end gap-1.5 text-sm font-bold text-foreground">
              <ShieldCheck className="h-4 w-4 text-bullish" />
              {getConfidenceText(opportunity.confidence)}
            </p>
          </div>
        </div>

        {/* Footer stats */}
        <div className="flex flex-wrap items-center gap-x-7 gap-y-2 pt-5">
          <div className="flex items-center gap-2">
            <Zap className={`h-4 w-4 ${positive ? 'text-bullish' : 'text-bearish'}`} />
            <span className="font-mono text-[11px] font-bold tabular-nums tracking-wide text-foreground">
              {positive ? '+' : ''}
              {opportunity.price_change_pct}%
            </span>
            <span className="label-caps text-[9.5px]">Growth</span>
          </div>
          <div className="label-caps text-[9.5px]">{opportunity.risk_level} Risk Level</div>
        </div>
      </div>
    </Link>
  );
}
