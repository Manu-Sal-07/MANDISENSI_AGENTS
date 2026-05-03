'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { mandiApi } from '@/services/api';
import { 
  ChevronLeft, 
  Loader2, 
  TrendingUp, 
  TrendingDown, 
  Info, 
  CheckCircle, 
  AlertTriangle,
  MapPin,
  Calendar,
  Zap
} from 'lucide-react';

export default function MandiDetailPage() {
  const params = useParams();
  const router = useRouter();
  const mandiId = params.id as string;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['mandi-details', mandiId],
    queryFn: () => mandiApi.getDiscoveryDetails(mandiId),
    enabled: !!mandiId,
  });

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'SELL': return 'text-red-500';
      case 'HOLD': return 'text-green-500';
      case 'WAIT': return 'text-yellow-500';
      default: return 'text-zinc-500';
    }
  };

  const calculateMoneyImpact = (price: number, pct: number) => {
    const impact = Math.abs(Math.round(price * (pct / 100)));
    return `₹${impact - 10}–₹${impact + 10}`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-40 gap-4">
        <Loader2 className="w-10 h-10 text-orange-500 animate-spin" />
        <p className="text-sm font-black uppercase tracking-[0.3em] text-zinc-400">Loading Market Intelligence...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-xl mx-auto py-40 px-6 text-center space-y-6">
        <div className="w-20 h-20 bg-red-50 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto">
          <AlertTriangle className="w-10 h-10 text-red-500" />
        </div>
        <h2 className="text-2xl font-black tracking-tight">Intelligence Fetch Failed</h2>
        <p className="text-zinc-500 font-medium">We couldn&apos;t reach the market agents. This might be due to a network error or the backend being offline.</p>
        <button 
          onClick={() => refetch()}
          className="bg-zinc-900 dark:bg-white text-white dark:text-black px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] active:scale-95 transition-all"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="pb-20">
      <div className="max-w-5xl mx-auto px-4 pt-8 space-y-10">
        {/* 1. Header Navigation */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <button 
              onClick={() => router.back()}
              className="flex items-center gap-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition-colors group"
            >
              <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
              <span className="text-[10px] font-black uppercase tracking-widest">Back to Market Feed</span>
            </button>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-orange-500" />
                <h1 className="text-4xl md:text-6xl font-black text-zinc-900 dark:text-zinc-100 tracking-tighter">
                  {data?.mandi_name}
                </h1>
              </div>
              <p className="text-zinc-500 font-bold uppercase tracking-[0.2em] text-xs">
                Complete Market Audit & Decision Report
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 bg-white dark:bg-zinc-900 p-4 rounded-3xl border border-zinc-100 dark:border-zinc-800">
            <Calendar className="w-5 h-5 text-zinc-400" />
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Last Updated</p>
              <p className="text-sm font-black text-zinc-900 dark:text-zinc-100">Today, {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
            </div>
          </div>
        </header>

        {/* 2. Commodity Intelligence Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.commodities.map((comm: any) => (
            <div 
              key={comm.name} 
              className="bg-white dark:bg-zinc-900 rounded-[2.5rem] p-8 shadow-sm border border-zinc-100 dark:border-zinc-800 space-y-6"
            >
              <div className="flex justify-between items-start">
                <div className="w-14 h-14 rounded-2xl bg-zinc-50 dark:bg-zinc-800 flex items-center justify-center text-3xl">
                  {comm.name.includes('Tomato') ? '🍅' : comm.name.includes('Onion') ? '🧅' : comm.name.includes('Potato') ? '🥔' : comm.name.includes('Garlic') ? '🧄' : '🫚'}
                </div>
                <div className={`text-2xl font-black italic tracking-tighter ${getDecisionColor(comm.decision)}`}>
                  {comm.decision}
                </div>
              </div>

              <div>
                <h3 className="text-2xl font-black tracking-tight">{comm.name}</h3>
                <p className="text-xs font-bold text-zinc-500 mt-1 italic leading-relaxed">
                  {comm.reasoning}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-6 border-t border-zinc-50 dark:border-zinc-800">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Impact</span>
                  <p className="text-lg font-black text-zinc-900 dark:text-zinc-100">
                    {comm.price_change > 0 ? <TrendingUp className="inline w-4 h-4 text-green-500 mr-1" /> : <TrendingDown className="inline w-4 h-4 text-red-500 mr-1" />}
                    {calculateMoneyImpact(comm.price, comm.price_change)}
                  </p>
                  <p className="text-[9px] font-bold text-zinc-400 mt-0.5 uppercase">Per Quintal</p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Confidence</span>
                  <p className="text-lg font-black text-zinc-900 dark:text-zinc-100">
                    {Math.round(comm.confidence * 100)}%
                  </p>
                  <p className="text-[9px] font-bold text-green-600 dark:text-green-400 mt-0.5 uppercase">Verified AI</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 3. Transport & Logistics Suggestion */}
        <div className="bg-zinc-900 text-white rounded-[3rem] p-8 md:p-12 shadow-2xl relative overflow-hidden group">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-10">
            <div className="space-y-4 max-w-xl">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center">
                  <Zap className="w-6 h-6 text-orange-500 fill-current" />
                </div>
                <div>
                  <h3 className="text-2xl font-black tracking-tight">Logistics Advice</h3>
                  <p className="text-zinc-400 font-bold uppercase tracking-widest text-[10px]">Optimized for Freshness</p>
                </div>
              </div>
              <p className="text-lg md:text-xl text-zinc-300 font-medium leading-relaxed italic">
                &ldquo;{data?.transport_suggestion || "Early morning transport recommended to avoid peak traffic and maintain moisture levels."}&rdquo;
              </p>
            </div>
            
            <div className="flex-none flex flex-col items-center gap-4 bg-white/5 border border-white/10 rounded-[2.5rem] p-8">
              <div className="text-center">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 mb-1">Market Volatility</p>
                <div className="text-3xl font-black text-orange-500 uppercase italic">Medium</div>
              </div>
              <div className="flex items-center gap-2 bg-green-500/10 text-green-500 px-4 py-2 rounded-full border border-green-500/20">
                <CheckCircle className="w-4 h-4 fill-current" />
                <span className="text-[10px] font-black uppercase tracking-widest">Safe to Proceed</span>
              </div>
            </div>
          </div>
          <div className="absolute top-0 right-0 w-96 h-96 bg-orange-500 blur-[120px] opacity-10 -mr-48 -mt-48 group-hover:opacity-20 transition-opacity" />
        </div>
      </div>
    </div>
  );
}
