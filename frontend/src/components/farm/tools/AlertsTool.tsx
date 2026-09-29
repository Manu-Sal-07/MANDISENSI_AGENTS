'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, BellPlus, Loader2, Trash2 } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { CropPicker, MandiPicker, PhonePicker } from './ContextPicker';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi, type AlertType } from '@/services/farmerApi';

const ALERT_LABELS: Record<AlertType, string> = {
  PRICE_ABOVE: 'Price goes above',
  PRICE_BELOW: 'Price falls below',
  DECISION_SELL: 'A SELL call is published',
  DECISION_HOLD: 'A HOLD call is published',
};

export default function AlertsTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { commodity, mandiId, phone } = useToolSelection();
  const [alertType, setAlertType] = useState<AlertType>('PRICE_ABOVE');
  const [threshold, setThreshold] = useState('');
  const queryClient = useQueryClient();

  const needsThreshold = alertType === 'PRICE_ABOVE' || alertType === 'PRICE_BELOW';

  const { data, isFetching } = useQuery({
    queryKey: ['alerts', phone],
    queryFn: () => farmerApi.listAlerts(phone),
    enabled: open && phone.length >= 6,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      farmerApi.createAlert(phone, commodity, mandiId, alertType, needsThreshold ? Number(threshold) : undefined),
    onSuccess: () => {
      setThreshold('');
      queryClient.invalidateQueries({ queryKey: ['alerts', phone] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (alertId: string) => farmerApi.deleteAlert(phone, alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts', phone] }),
  });

  const canCreate = phone.length >= 6 && (!needsThreshold || Number(threshold) > 0);

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Price Alerts"
      subtitle="Get notified the moment your price hits"
      accentColour="#d1874f"
      icon={<Bell className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <PhonePicker />
        <CropPicker />
        <MandiPicker />

        <label className="block">
          <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
            Notify me when
          </span>
          <select
            value={alertType}
            onChange={(event) => setAlertType(event.target.value as AlertType)}
            className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold text-[var(--farm-ink)]"
          >
            {(Object.keys(ALERT_LABELS) as AlertType[]).map((type) => (
              <option key={type} value={type}>
                {ALERT_LABELS[type]}
              </option>
            ))}
          </select>
        </label>

        {needsThreshold && (
          <input
            type="number"
            min={1}
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
            placeholder="₹ per quintal"
            className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-bold tabular-nums text-[var(--farm-ink)] placeholder:font-normal placeholder:text-[var(--farm-ink-faint)]"
          />
        )}

        <button
          type="button"
          disabled={!canCreate || createMutation.isPending}
          onClick={() => createMutation.mutate()}
          className="farm-focus farm-tap flex w-full items-center justify-center gap-2 rounded-xl text-sm font-bold text-white transition-opacity disabled:opacity-40"
          style={{ background: '#d1874f' }}
        >
          {createMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <BellPlus className="h-4 w-4" />
          )}
          Create alert
        </button>

        {phone.length >= 6 && (
          <div className="space-y-2 border-t border-[var(--farm-line)] pt-3">
            <p className="text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
              Your alerts
            </p>
            {isFetching && <Loader2 className="h-4 w-4 animate-spin text-[var(--farm-ink-faint)]" />}
            {!isFetching && (data?.alerts.length ?? 0) === 0 && (
              <p className="text-sm text-[var(--farm-ink-faint)]">No alerts yet.</p>
            )}
            {(data?.alerts ?? []).map((alert, index) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between rounded-xl border border-[var(--farm-line)] px-3.5 py-2.5"
              >
                <div className="text-sm">
                  <p className="font-bold capitalize text-[var(--farm-ink)]">
                    {alert.commodity} · {alert.mandi_id.replace('_apmc', '').replace('_', ' ')}
                  </p>
                  <p className="text-xs text-[var(--farm-ink-faint)]">
                    {ALERT_LABELS[alert.alert_type]}
                    {alert.threshold ? ` ₹${alert.threshold}` : ''}
                  </p>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(alert.id)}
                  aria-label="Delete alert"
                  className="farm-focus rounded-full p-2 text-[var(--farm-ink-faint)] hover:bg-[var(--farm-line)]"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </ToolSheet>
  );
}
