'use client';

import React, { useState } from 'react';
import LocationBar from '@/components/LocationBar';
import SearchBar from '@/components/SearchBar';
import OpportunityFeed from '@/components/OpportunityFeed';
import QuickDecisionBar from '@/components/QuickDecisionBar';
import { mandiApi } from '@/services/api';
import { QueryResponse } from '@/types/mandi';
import { RefreshCw, CheckCircle } from 'lucide-react';

/**
 * Phase 7: Swiggy-style UI — Mandi Discovery & Smart Query
 */
export default function Homepage() {
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showQuickDecisions, setShowQuickDecisions] = useState(true);

  const handleSmartSearch = async (query: string) => {
    setIsSearching(true);
    setSearchResult(null);
    setError(null);
    try {
      const result = await mandiApi.predictQuery(query);
      setSearchResult(result);
    } catch (err) {
      setError("Data not available right now. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'SELL': return 'text-red-500';
      case 'HOLD': return 'text-green-500';
      case 'WAIT': return 'text-yellow-500';
      default: return 'text-zinc-500';
    }
  };

  return (
    <div className="flex flex-col">
      {/* 1. Contextual Header */}
      <LocationBar />
      
      <div className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 space-y-10">
        {/* 2. Smart Query Input */}
        <section className="space-y-4">
          <div className="text-center space-y-2">
            <h1 className="text-4xl md:text-6xl font-black tracking-tighter text-zinc-900 dark:text-zinc-100">
              MandiSense <span className="text-emerald-600">AI</span>
            </h1>
            <p className="text-zinc-500 dark:text-zinc-400 font-bold uppercase tracking-[0.3em] text-[10px]">
              Daily Decision Guide for Farmers
            </p>
          </div>
          <SearchBar onSearch={handleSmartSearch} isLoading={isSearching} />
          {error && <p className="text-center text-red-500 text-xs font-bold">{error}</p>}
        </section>

        {/* 2.5 Quick Decision Bar (Toggleable) */}
        <section className="space-y-4">
          <div className="flex justify-between items-center px-2">
            <label className="flex items-center gap-2 cursor-pointer group">
              <input 
                type="checkbox" 
                checked={showQuickDecisions} 
                onChange={(e) => setShowQuickDecisions(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-300 text-orange-500 focus:ring-orange-500"
              />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400 group-hover:text-zinc-600 transition-colors">
                Show Quick Advice
              </span>
            </label>
          </div>
          {showQuickDecisions && <QuickDecisionBar />}
        </section>

        {/* 3. Search Results (if any) */}
        {searchResult && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-zinc-950 text-white rounded-[2.5rem] p-8 md:p-12 shadow-2xl relative overflow-hidden border border-white/5">
              <div className="relative z-10 space-y-8">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500">
                      Strategy for {searchResult?.metadata?.mandi_id?.replace('_apmc', '').toUpperCase() || 'MARKET'}
                    </span>
                    <h2 className={`text-6xl md:text-8xl font-black tracking-tighter ${getDecisionColor(searchResult.decision)}`}>
                      {searchResult.decision}
                    </h2>
                  </div>
                  <button 
                    onClick={() => setSearchResult(null)}
                    className="text-zinc-500 hover:text-white transition-colors"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="space-y-6 max-w-2xl">
                  <p className="text-2xl md:text-3xl font-bold tracking-tight leading-tight">
                    {searchResult.summary}
                  </p>
                  
                  <div className="space-y-4">
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Reasoning</h4>
                    <p className="text-zinc-400 font-medium leading-relaxed">
                      {searchResult.reasoning}
                    </p>
                  </div>

                  <div className="bg-white/5 rounded-3xl p-6 border border-white/5">
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-400 mb-2">Market Insight</h4>
                    <p className="text-lg font-bold text-zinc-200 italic">
                      &ldquo;{searchResult.market_insight}&rdquo;
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6 pt-8 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
                      {searchResult?.metadata?.confidence > 0.85 ? 'High confidence' : 'Medium confidence'}
                    </span>
                  </div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Data Updated Today</div>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-96 h-96 bg-zinc-800 blur-[120px] opacity-20 -mr-48 -mt-48 pointer-events-none" />
            </div>
          </section>
        )}
        
        {/* 4. Location-Aware Mandi Discovery */}
        <section className="space-y-6 pt-6">
          <div className="px-2 flex flex-col gap-1">
            <h2 className="text-2xl font-black tracking-tighter text-zinc-900 dark:text-zinc-100 italic">Market Intelligence</h2>
            <p className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.3em]">Nearby Mandis & Signal Audits</p>
          </div>
          
          <OpportunityFeed variant="grid" />
        </section>

        {/* 6. Footer Trust Signals */}
        <section className="py-10 text-center space-y-4">
          <div className="flex items-center justify-center gap-4 text-zinc-400">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Safe & Trusted</span>
            </div>
            <div className="flex items-center gap-1.5">
              <RefreshCw className="w-4 h-4 text-orange-500" />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Real-time Trends</span>
            </div>
          </div>
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.4em]">Powered by MandiSense AI Engine v3</p>
        </section>
      </div>

      {/* Persistent Bottom Navigation Placeholder */}
      <div className="fixed bottom-0 left-0 right-0 h-16 bg-white/80 dark:bg-black/80 backdrop-blur-xl border-t border-zinc-100 dark:border-zinc-900 flex items-center justify-around px-6 z-50">
        <div className="w-6 h-6 bg-zinc-900 dark:bg-zinc-100 rounded-lg"></div>
        <div className="w-6 h-6 bg-zinc-100 dark:bg-zinc-800 rounded-lg"></div>
        <div className="w-6 h-6 bg-zinc-100 dark:bg-zinc-800 rounded-lg"></div>
      </div>
    </div>
  );
}
