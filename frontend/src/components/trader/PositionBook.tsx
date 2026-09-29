'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Briefcase, Plus, Trash2 } from 'lucide-react';
import { ToolCard, LoadingRow, CommodityPicker, MandiPicker, formatRupees } from './shared';
import { traderApi, type PositionSide } from '@/services/traderApi';

const BOOK_ID_STORAGE_KEY = 'mandisense-trader-book-id';

function getOrCreateBookId(): string {
  try {
    const existing = window.localStorage.getItem(BOOK_ID_STORAGE_KEY);
    if (existing) return existing;
    const created = `book_${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(BOOK_ID_STORAGE_KEY, created);
    return created;
  } catch {
    return 'book_default';
  }
}

/**
 * Real position book and risk — replaces the Command Center's ₹ Lakhs
 * exposure figures, which were `COMMODITY_VOLUMES[commodity] x price x
 * change` against a fixed table nobody entered (see the trader audit).
 * Everything here is priced against positions the trader actually recorded,
 * using historical simulation across the real joint return distribution
 * when enough shared history exists (`trader/positions.py`), and saying so
 * plainly when it doesn't.
 */
export default function PositionBook({
  mandis,
}: {
  mandis: Array<{ mandi_id: string; mandi_name: string }>;
}) {
  const [bookId, setBookId] = useState<string | null>(null);
  const [commodity, setCommodity] = useState('tomato');
  const [mandiId, setMandiId] = useState(mandis[0]?.mandi_id ?? 'kolar_apmc');
  const [quantity, setQuantity] = useState(10);
  const [side, setSide] = useState<PositionSide>('LONG');
  const queryClient = useQueryClient();

  React.useEffect(() => {
    setBookId(getOrCreateBookId());
  }, []);

  const { data: risk, isFetching } = useQuery({
    queryKey: ['trader-risk', bookId],
    queryFn: () => traderApi.assessRisk(bookId as string),
    enabled: !!bookId,
  });

  const addMutation = useMutation({
    mutationFn: () => traderApi.addPosition(bookId as string, commodity, mandiId, quantity, undefined, side),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trader-risk', bookId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (positionId: string) => traderApi.deletePosition(bookId as string, positionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trader-risk', bookId] }),
  });

  return (
    <ToolCard
      title="Position Book & Risk"
      subtitle="Real exposure, priced against what you actually hold"
      icon={<Briefcase className="h-4.5 w-4.5" />}
      accent="#f472b6"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <CommodityPicker value={commodity} onChange={setCommodity} />
        <MandiPicker value={mandiId} onChange={setMandiId} mandis={mandis} />
        <select
          value={side}
          onChange={(e) => setSide(e.target.value as PositionSide)}
          className="rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground"
        >
          <option value="LONG">LONG</option>
          <option value="SHORT">SHORT</option>
        </select>
        <input
          type="number"
          min={1}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
          className="w-16 rounded-lg border border-border bg-surface-2 px-2 py-1.5 text-xs font-semibold tabular-nums text-foreground"
        />
        <button
          onClick={() => addMutation.mutate()}
          disabled={!bookId || addMutation.isPending}
          className="flex items-center gap-1 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-bold text-white disabled:opacity-40"
        >
          <Plus className="h-3.5 w-3.5" /> Add
        </button>
      </div>

      {isFetching && <LoadingRow label="Assessing portfolio risk…" />}

      {!isFetching && risk?.status === 'EMPTY' && (
        <p className="py-4 text-xs text-neutral-signal">No positions recorded yet — add one above.</p>
      )}

      {!isFetching && risk?.status === 'OK' && (
        <>
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded-lg bg-surface-2 p-2.5">
              <p className="text-[9px] font-bold uppercase tracking-wider text-neutral-signal">Net exposure</p>
              <p className="font-mono text-sm font-bold text-foreground">{formatRupees(risk.net_exposure)}</p>
            </div>
            <div className="rounded-lg bg-surface-2 p-2.5">
              <p className="text-[9px] font-bold uppercase tracking-wider text-neutral-signal">
                5% worst case ({risk.horizon_days}d)
              </p>
              <p className="font-mono text-sm font-bold" style={{ color: 'var(--bearish)' }}>
                {formatRupees(risk.portfolio?.worst_case_95)}
              </p>
            </div>
          </div>
          {risk.portfolio?.note && (
            <p className="mt-2 text-[10px] italic text-neutral-signal">{risk.portfolio.note}</p>
          )}

          <div className="mt-3 space-y-1.5">
            {(risk.positions ?? []).map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-center justify-between rounded-lg bg-surface-2 px-2.5 py-1.5 text-[11px]"
              >
                <span className="capitalize text-foreground">
                  {p.side} {p.quantity_quintals}q {p.commodity.replace('_', ' ')}
                </span>
                <span className="flex items-center gap-2">
                  {p.status === 'OK' ? (
                    <span className="font-mono font-bold" style={{ color: (p.exposure ?? 0) >= 0 ? 'var(--bullish)' : 'var(--bearish)' }}>
                      {formatRupees(p.exposure)}
                    </span>
                  ) : (
                    <span className="text-neutral-signal">no price</span>
                  )}
                  <button onClick={() => deleteMutation.mutate(p.id)} className="text-neutral-signal hover:text-bearish">
                    <Trash2 className="h-3 w-3" />
                  </button>
                </span>
              </motion.div>
            ))}
          </div>
        </>
      )}
    </ToolCard>
  );
}
