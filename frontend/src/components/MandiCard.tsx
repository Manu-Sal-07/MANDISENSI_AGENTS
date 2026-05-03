'use client';

import React from 'react';
import { ChevronRight, Zap, CheckCircle } from 'lucide-react';
import Link from 'next/link';

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

export default function MandiCard({ opportunity }: MandiCardProps) {
  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'SELL': return 'text-red-600 dark:text-red-500';
      case 'HOLD': return 'text-emerald-600 dark:text-emerald-500';
      case 'WAIT': return 'text-amber-500';
      default: return 'text-zinc-500';
    }
  };

  const getConfidenceText = (conf: number) => {
    if (conf > 0.8) return 'High confidence';
    if (conf > 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  return (
    <Link href={`/mandi/${opportunity.id}`} className="block group">
      <div className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm rounded-[2.5rem] p-8 floating-card floating-card-hover border border-white dark:border-zinc-800 transition-all duration-500 group-active:scale-[0.98]">
        {/* 1. Card Header */}
        <div className="flex justify-between items-start mb-8">
          <div className="flex gap-5 items-center">
            <div className="w-16 h-16 rounded-3xl bg-zinc-50 dark:bg-zinc-800 flex items-center justify-center text-3xl shadow-inner group-hover:bg-emerald-500/10 transition-colors">
              {opportunity.hot_commodity.includes('Tomato') ? '🍅' : opportunity.hot_commodity.includes('Onion') ? '🧅' : '🥔'}
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                  {opportunity.mandi_name.toUpperCase()}
                </span>
              </div>
              <h3 className="text-3xl font-black text-zinc-900 dark:text-zinc-100 tracking-tighter">
                {opportunity.hot_commodity}
              </h3>
            </div>
          </div>
          <div className="w-12 h-12 rounded-2xl border border-zinc-100 dark:border-zinc-800 flex items-center justify-center bg-white dark:bg-zinc-900 group-hover:bg-zinc-900 group-hover:text-white dark:group-hover:bg-white dark:group-hover:text-black transition-all">
            <ChevronRight className="w-6 h-6" />
          </div>
        </div>

        {/* 2. Primary Decision Insight */}
        <div className="flex items-end justify-between border-b border-zinc-50 dark:border-zinc-900 pb-8">
          <div className="space-y-1.5">
            <div className={`text-6xl font-black tracking-tighter italic ${getDecisionColor(opportunity.decision)}`}>
              {opportunity.decision}
            </div>
            <p className="text-sm font-bold text-zinc-500 max-w-[220px] line-clamp-1 italic">
              {opportunity.reasoning || "Analyzing market signals..."}
            </p>
          </div>
          <div className="text-right">
             <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Trust Score</span>
             <p className="text-sm font-black text-zinc-900 dark:text-zinc-100 flex items-center justify-end gap-1.5">
               <CheckCircle className="w-4 h-4 text-emerald-500 fill-current" />
               {getConfidenceText(opportunity.confidence)}
             </p>
          </div>
        </div>

        {/* 3. Footer Stats */}
        <div className="flex items-center gap-8 pt-6">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500 fill-current" />
            <span className="text-[11px] font-black uppercase tracking-widest text-zinc-600 dark:text-zinc-400">
              {opportunity.price_change_pct > 0 ? `+${opportunity.price_change_pct}%` : `${opportunity.price_change_pct}%`} Growth
            </span>
          </div>
          <div className="text-[11px] font-black uppercase tracking-widest text-zinc-400">
            {opportunity.risk_level} Risk Level
          </div>
        </div>
      </div>
    </Link>
  );
}
