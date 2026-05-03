'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { mandiApi } from '@/services/api';
import { Zap, Loader2, MapPin } from 'lucide-react';

export default function QuickDecisionBar() {
  const { data, isLoading } = useQuery({
    queryKey: ['quick-decisions'],
    queryFn: () => mandiApi.getQuickDecisions('bengaluru'),
    staleTime: 1000 * 60 * 2, // 2 mins
  });

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'SELL': return 'text-red-600 dark:text-red-400';
      case 'HOLD': return 'text-emerald-600 dark:text-emerald-400';
      default: return 'text-amber-500';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-4 bg-white dark:bg-zinc-900/50 p-6 rounded-[2rem] border border-dashed border-zinc-200 dark:border-zinc-800 animate-pulse">
        <Loader2 className="w-5 h-5 text-zinc-400 animate-spin" />
        <span className="text-[11px] font-black uppercase tracking-widest text-zinc-400">Syncing with market agents...</span>
      </div>
    );
  }

  return (
    <div className="bg-white/60 dark:bg-zinc-900/60 backdrop-blur-md rounded-[3rem] p-8 floating-card border border-white dark:border-zinc-800 relative overflow-hidden group">
      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-amber-600 rounded-[1.8rem] flex items-center justify-center shadow-lg shadow-orange-500/20 group-hover:rotate-6 transition-transform">
            <Zap className="w-7 h-7 text-white fill-current" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-400">{data?.location || 'BENGALURU REGION'}</span>
            </div>
            <h3 className="text-xl font-black tracking-tight text-zinc-900 dark:text-zinc-100">Market Flash Advice</h3>
          </div>
        </div>

        <div className="flex gap-4 overflow-x-auto no-scrollbar pb-1 lg:pb-0">
          {data?.decisions.map((item: any) => (
            <div key={item.commodity} className="flex-none bg-white dark:bg-white/5 border border-zinc-100 dark:border-white/5 rounded-[2rem] px-6 py-4 flex items-center gap-5 hover:border-emerald-500/30 transition-all group/item shadow-sm hover:shadow-md">
              <span className="text-3xl group-hover/item:scale-110 transition-transform">
                {item.commodity.includes('Tomato') ? '🍅' : item.commodity.includes('Onion') ? '🧅' : item.commodity.includes('Potato') ? '🥔' : item.commodity.includes('Garlic') ? '🧄' : '🫚'}
              </span>
              <div>
                <p className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.1em]">{item.commodity}</p>
                <p className={`text-lg font-black italic tracking-tighter ${getDecisionColor(item.decision)}`}>
                  {item.decision}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute top-0 right-0 w-48 h-48 bg-emerald-500 blur-[80px] opacity-5 -mr-24 -mt-24 group-hover:opacity-10 transition-opacity" />
    </div>
  );
}
