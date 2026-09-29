'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Clock, Loader2, PackageX } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker, QuantityPicker } from './ContextPicker';
import UnavailableNotice from './UnavailableNotice';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type HoldOrRotResult } from '@/services/farmerApi';
import { formatDate, formatRupees } from '@/lib/format';

export default function HoldOrRotTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId, quantityQuintals } = useToolSelection();

  const { data, isFetching } = useQuery<HoldOrRotResult>({
    queryKey: ['hold-or-rot', commodity, mandiId, quantityQuintals],
    queryFn: () => farmerApi.holdOrSell(commodity, mandiId, quantityQuintals),
    enabled: open,
  });

  const isHold = data?.recommendation === 'HOLD';

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Hold or Sell"
      subtitle="Waiting has a cost — is it worth it?"
      accentColour="var(--turmeric)"
      icon={<PackageX className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <CropPicker />
        <div className="grid grid-cols-2 gap-3">
          <MandiPicker />
          <QuantityPicker />
        </div>

        {data?.shelf_profile && (
          <div className="flex items-center gap-2 rounded-xl bg-[var(--farm-line)]/40 px-3.5 py-2.5 text-xs font-semibold text-[var(--farm-ink-soft)]">
            <Clock className="h-3.5 w-3.5" />
            Keeps about {data.shelf_profile.shelf_life_days} day(s) · {data.shelf_profile.category.replace('_', ' ')}
          </div>
        )}

        {isFetching && (
          <div className="flex items-center gap-2 py-8 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Weighing spoilage against the forecast…
          </div>
        )}

        {!isFetching && data?.status === 'UNAVAILABLE' && <UnavailableNotice reason={data.reason} />}

        {!isFetching && data?.status === 'OK' && (
          <>
            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', stiffness: 280, damping: 22 }}
              className="rounded-2xl p-5 text-center"
              style={{ background: isHold ? 'var(--call-hold-wash)' : 'var(--call-sell-wash)' }}
            >
              <p
                className="farm-display text-3xl"
                style={{ color: isHold ? 'var(--call-hold)' : 'var(--call-sell)' }}
              >
                {isHold ? 'Hold' : 'Sell now'}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-[var(--farm-ink-soft)]">{data.reasoning}</p>
            </motion.div>

            {data.options && data.options.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
                  Net value after spoilage, by day
                </p>
                {data.options.map((option, index) => {
                  const best = option === data.best_option;
                  return (
                    <motion.div
                      key={option.horizon_days}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.06 }}
                      className="flex items-center justify-between rounded-xl border px-3.5 py-2.5"
                      style={{
                        borderColor: best ? 'var(--leaf)' : 'var(--farm-line)',
                        background: best ? 'var(--leaf-wash)' : 'transparent',
                      }}
                    >
                      <div>
                        <p className="text-sm font-bold text-[var(--farm-ink)]">
                          {formatDate(option.target_date)}
                        </p>
                        <p className="text-xs text-[var(--farm-ink-faint)]">
                          spoilage: −{formatRupees(option.spoilage_cost)}
                        </p>
                      </div>
                      <span className="font-mono text-base font-black text-[var(--farm-ink)]">
                        {formatRupees(option.net_value)}
                      </span>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </ToolSheet>
  );
}
