'use client';

import { Compass } from 'lucide-react';
import { useLocation } from '@/hooks/useLocation';
import { useAppStore } from '@/store/useAppStore';

export default function LocationBar() {
  const { requestLocation } = useLocation();
  const { personalizationStatus, viewMode, resetToDefault } = useAppStore();

  const isRequesting = personalizationStatus === 'requesting';
  const isPersonalized = viewMode === 'personalized';

  return (
    <div className="glass-panel sticky top-16 z-40 flex items-center justify-between px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3.5">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-2xl transition-all"
          style={
            isPersonalized
              ? { background: 'var(--accent)', color: 'white', boxShadow: '0 8px 18px -8px var(--accent-glow)' }
              : { background: 'var(--surface-2)', color: 'var(--neutral-signal)' }
          }
        >
          <Compass className={`h-4.5 w-4.5 ${isRequesting ? 'animate-spin' : ''}`} />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold uppercase tracking-tight text-foreground">
              {isPersonalized ? 'Live Local Feed' : 'Bengaluru Market'}
            </span>
            <div className="flex items-center gap-1 rounded-full bg-bullish/10 px-2 py-0.5">
              <span className="live-dot" />
              <span className="text-[8px] font-black uppercase tracking-widest text-bullish">Active</span>
            </div>
          </div>
          <div className="mt-0.5 flex items-center gap-2">
            <span className="label-caps text-[9.5px]">
              {isPersonalized ? 'Precise geotagged data' : 'Regional intelligence hub'}
            </span>
            <button
              onClick={isPersonalized ? resetToDefault : requestLocation}
              disabled={isRequesting}
              className="text-[9.5px] font-black uppercase tracking-widest text-accent-strong hover:underline disabled:opacity-50"
            >
              {isRequesting ? 'Locating…' : isPersonalized ? '[ Clear ]' : '[ Sync GPS ]'}
            </button>
          </div>
        </div>
      </div>

      <button className="btn-ghost hidden text-[10px] !py-2 sm:inline-flex">Switch Location</button>
    </div>
  );
}
