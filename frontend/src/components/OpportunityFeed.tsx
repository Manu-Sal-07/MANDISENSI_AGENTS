'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import MandiCard from './MandiCard';
import SkeletonCard from './SkeletonCard';
import { mandiApi } from '@/services/api';
import { Search, MapPin, WifiOff, Loader2 } from 'lucide-react';

interface OpportunityFeedProps {
  variant?: 'grid' | 'horizontal';
}

interface Opportunity {
  id: string;
  mandi_name: string;
  hot_commodity: string;
  decision: 'SELL' | 'HOLD' | 'WAIT';
  reasoning?: string;
  price_change_pct: number;
  confidence: number;
  risk_level: string;
}

export default function OpportunityFeed({ variant = 'grid' }: OpportunityFeedProps) {
  const [location, setLocation] = useState('bengaluru');
  const [isDetecting, setIsDetecting] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLocation('bengaluru');
      setIsDetecting(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  const { data: feedData, isLoading: isFeedLoading, isError } = useQuery({
    queryKey: ['discovery-feed', location],
    queryFn: () => mandiApi.getDiscoveryFeed(location),
    enabled: !isDetecting,
    staleTime: 1000 * 60 * 5,
  });

  if (isDetecting || (isFeedLoading && !feedData)) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 px-1">
          <Loader2 className="h-4 w-4 animate-spin text-neutral-signal" />
          <span className="label-caps text-[10px]">Detecting nearest mandis…</span>
        </div>
        <div className={variant === 'grid' ? 'grid grid-cols-1 gap-6 md:grid-cols-2' : 'no-scrollbar flex gap-6 overflow-x-auto pb-4'}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={variant === 'horizontal' ? 'w-[300px] flex-none' : ''}>
              <SkeletonCard />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-accent-strong" />
          <span className="label-caps text-[10px] text-foreground">
            Mandis near {location.charAt(0).toUpperCase() + location.slice(1)}
          </span>
        </div>
        {isError && <WifiOff className="h-4 w-4 text-bearish" />}
      </div>

      {!feedData || feedData.length === 0 ? (
        <EmptyState />
      ) : (
        <div
          className={
            variant === 'grid'
              ? 'grid grid-cols-1 gap-6 pb-12 lg:grid-cols-2'
              : 'no-scrollbar flex snap-x gap-6 overflow-x-auto pb-10'
          }
        >
          {feedData.map((opp: Opportunity, i: number) => (
            <motion.div
              key={opp.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className={variant === 'horizontal' ? 'w-[320px] flex-none snap-start' : ''}
            >
              <MandiCard opportunity={opp} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

const EmptyState = React.memo(() => (
  <div className="flex flex-col items-center justify-center px-4 py-20 text-center">
    <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-surface-2">
      <Search className="h-8 w-8 text-neutral-signal" />
    </div>
    <h3 className="text-xl font-bold tracking-tight text-foreground">No mandis found nearby</h3>
    <p className="mt-2 max-w-xs text-sm leading-relaxed text-neutral-signal">
      Try searching for a specific location or check back later.
    </p>
  </div>
));

EmptyState.displayName = 'EmptyState';
