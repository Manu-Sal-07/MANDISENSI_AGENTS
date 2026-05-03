'use client';

import { MapPin, RefreshCw, Compass } from 'lucide-react';
import { useLocation } from '@/hooks/useLocation';
import { useAppStore } from '@/store/useAppStore';

export default function LocationBar() {
  const { requestLocation } = useLocation();
  const { personalizationStatus, viewMode, resetToDefault } = useAppStore();

  const isRequesting = personalizationStatus === 'requesting';
  const isPersonalized = viewMode === 'personalized';

  return (
    <div className="bg-white/80 dark:bg-black/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-40 border-b border-zinc-100 dark:border-zinc-900">
      <div className="flex items-center gap-4">
        <div className={`p-2 rounded-2xl transition-all ${
          isPersonalized ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-500'
        }`}>
          <Compass className={`w-5 h-5 ${isRequesting ? 'animate-spin' : ''}`} />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-black text-sm tracking-tight text-zinc-900 dark:text-zinc-100 uppercase">
              {isPersonalized ? 'Live Local Feed' : 'Bengaluru Market'}
            </span>
            <div className="flex items-center gap-1 bg-emerald-500/10 px-2 py-0.5 rounded-full">
               <span className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" />
               <span className="text-[8px] font-black text-emerald-600 uppercase tracking-widest">Active</span>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">
              {isPersonalized ? 'Precise Geotagged Data' : 'Regional Intelligence Hub'}
            </span>
            <button 
              onClick={isPersonalized ? resetToDefault : requestLocation}
              disabled={isRequesting}
              className="text-emerald-600 text-[10px] font-black uppercase hover:underline disabled:opacity-50 tracking-widest"
            >
              {isRequesting ? 'Locating...' : isPersonalized ? '[ Clear ]' : '[ Sync GPS ]'}
            </button>
          </div>
        </div>
      </div>

      <button className="text-[10px] font-black uppercase tracking-[0.2em] bg-zinc-50 dark:bg-zinc-900 px-4 py-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-all border border-zinc-100 dark:border-zinc-800 active:scale-95">
        Switch Location
      </button>
    </div>
  );
}
