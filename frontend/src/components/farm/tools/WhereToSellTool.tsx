'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Crown, Loader2, MapPinned, Navigation } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, QuantityPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type WhereToSellResult } from '@/services/farmerApi';
import { formatRupees } from '@/lib/format';

export default function WhereToSellTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId, quantityQuintals } = useToolSelection();
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [locating, setLocating] = useState(false);

  const origin = coords ? { lat: coords.lat, lon: coords.lon } : { mandiId };

  const { data, isFetching } = useQuery<WhereToSellResult>({
    queryKey: ['where-to-sell', commodity, mandiId, coords, quantityQuintals],
    queryFn: () => farmerApi.whereToSell(commodity, origin, quantityQuintals),
    enabled: open,
  });

  const useMyLocation = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({ lat: position.coords.latitude, lon: position.coords.longitude });
        setLocating(false);
      },
      () => setLocating(false),
      { timeout: 8000 }
    );
  };

  const mandis = data?.mandis ?? [];
  const bestPrice = mandis[0]?.net_price_per_quintal ?? 0;

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Where to Sell"
      subtitle="Best net price after transport, nearby"
      accentColour="var(--accent-strong, #2f6fed)"
      icon={<MapPinned className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <div className="grid grid-cols-2 gap-3">
          <QuantityPicker />
          <button
            type="button"
            onClick={useMyLocation}
            disabled={locating}
            className="farm-focus farm-tap mt-6 flex items-center justify-center gap-1.5 rounded-xl border border-[var(--farm-line)] bg-white text-sm font-bold text-[var(--leaf)] disabled:opacity-50"
          >
            {locating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Navigation className="h-4 w-4" />}
            {coords ? 'Located' : 'Use my location'}
          </button>
        </div>

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Comparing nearby mandis…
          </div>
        )}

        {!isFetching && data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {!isFetching && data?.status === 'OK' && (
          <div className="space-y-2">
            {data.transport_rate_per_quintal_per_km !== undefined && (
              <p className="text-xs text-[var(--farm-ink-faint)]">
                Assumes ₹{data.transport_rate_per_quintal_per_km}/quintal/km transport — adjust for your own truck.
              </p>
            )}
            {mandis.map((mandi, index) => (
              <motion.div
                key={mandi.mandi_id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between rounded-2xl border px-4 py-3"
                style={{
                  borderColor: index === 0 ? 'var(--leaf)' : 'var(--farm-line)',
                  background: index === 0 ? 'var(--leaf-wash)' : 'var(--farm-paper)',
                }}
              >
                <div>
                  <p className="flex items-center gap-1.5 text-sm font-bold text-[var(--farm-ink)]">
                    {index === 0 && <Crown className="h-3.5 w-3.5" style={{ color: 'var(--leaf)' }} />}
                    {mandi.mandi_name}
                  </p>
                  <p className="text-xs text-[var(--farm-ink-faint)]">
                    {mandi.distance_km} km · gross {formatRupees(mandi.gross_price_per_quintal)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-base font-black text-[var(--farm-ink)]">
                    {formatRupees(mandi.net_price_per_quintal)}
                  </p>
                  <p className="text-[10px] uppercase tracking-wide text-[var(--farm-ink-faint)]">net/quintal</p>
                </div>
              </motion.div>
            ))}
            {mandis.length > 1 && (
              <p className="pt-1 text-center text-xs text-[var(--farm-ink-faint)]">
                Best mandi beats the worst by {formatRupees(data.best_over_worst)}/quintal
              </p>
            )}
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
