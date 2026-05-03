'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import MandiCard from './MandiCard';
import SkeletonCard from './SkeletonCard';
import { mandiApi } from '@/services/api';
import { Search, MapPin, WifiOff, Loader2 } from 'lucide-react';

interface OpportunityFeedProps {
  variant?: 'grid' | 'horizontal';
}

export default function OpportunityFeed({ variant = 'grid' }: OpportunityFeedProps) {
  const [location, setLocation] = useState('bengaluru');
  const [isDetecting, setIsDetecting] = useState(true);

  // 1. Simulate Location Detection
  useEffect(() => {
    const timer = setTimeout(() => {
      // In a real app, use Geolocation API here
      setLocation('bengaluru');
      setIsDetecting(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // 2. Fetch Discovery Feed
  const { data: feedData, isLoading: isFeedLoading, isError } = useQuery({
    queryKey: ['discovery-feed', location],
    queryFn: () => mandiApi.getDiscoveryFeed(location),
    enabled: !isDetecting,
    staleTime: 1000 * 60 * 5, // Cache for 5 mins
  });

  if (isDetecting || (isFeedLoading && !feedData)) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 px-4">
          <Loader2 className="w-4 h-4 text-zinc-400 animate-spin" />
          <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Detecting nearest mandis...</span>
        </div>
        <div className={variant === 'grid' ? "grid grid-cols-1 md:grid-cols-2 gap-6 p-4" : "flex gap-6 overflow-x-auto no-scrollbar pb-4"}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={variant === 'horizontal' ? 'flex-none w-[300px]' : ''}>
              <SkeletonCard />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="px-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-orange-500" />
          <span className="text-[10px] font-black text-zinc-900 dark:text-zinc-100 uppercase tracking-widest">
            Mandis near {location.charAt(0).toUpperCase() + location.slice(1)}
          </span>
        </div>
        {isError && <WifiOff className="w-4 h-4 text-red-500" />}
      </div>

      {!feedData || feedData.length === 0 ? (
        <EmptyState />
      ) : (
        <div className={variant === 'grid' ? "grid grid-cols-1 lg:grid-cols-2 gap-8 px-4 pb-12" : "flex gap-6 overflow-x-auto no-scrollbar px-4 pb-10 snap-x"}>
          {feedData.map((opp: any) => (
            <div key={opp.id} className={variant === 'horizontal' ? 'flex-none w-[320px] snap-start' : ''}>
              <MandiCard opportunity={opp} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const EmptyState = React.memo(() => (
  <div className="flex flex-col items-center justify-center py-20 px-4 text-center animate-in fade-in zoom-in duration-500">
    <div className="w-20 h-20 bg-zinc-100 dark:bg-zinc-900 rounded-full flex items-center justify-center mb-4 shadow-inner">
      <Search className="w-8 h-8 text-zinc-400" />
    </div>
    <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">No mandis found nearby</h3>
    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 max-w-xs leading-relaxed">
      Try searching for a specific location or check back later.
    </p>
  </div>
));

EmptyState.displayName = 'EmptyState';
