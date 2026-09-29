'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import ProduceIcon, { resolveProduce, produceScript, type ProduceName } from '../ProduceIcon';
import { useToolSelection } from '@/context/ToolContext';
import { useLanguage } from '@/context/LanguageContext';
import { farmerApi } from '@/services/farmerApi';

const CROPS: ProduceName[] = ['tomato', 'onion', 'potato', 'garlic', 'ginger', 'dry_chillies'];

/**
 * The crop + mandi selector every tool panel opens with.
 *
 * Shown compactly (a chip row plus a dropdown) rather than as its own
 * screen, because it is a refinement of what `ToolContext` already
 * remembers from last time — most opens need no change here at all.
 */
export function CropPicker() {
  const { commodity, setCommodity } = useToolSelection();
  const { lang } = useLanguage();

  return (
    <div className="flex flex-wrap gap-2">
      {CROPS.map((crop) => {
        const produce = resolveProduce(crop);
        const script = produceScript(produce, lang);
        const active = commodity === crop;
        return (
          <button
            key={crop}
            type="button"
            onClick={() => setCommodity(crop)}
            className="farm-focus flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold transition-colors"
            style={{
              borderColor: active ? 'var(--leaf)' : 'var(--farm-line)',
              background: active ? 'var(--leaf-wash)' : 'var(--farm-paper)',
              color: active ? 'var(--leaf-deep)' : 'var(--farm-ink-soft)',
            }}
          >
            <ProduceIcon name={crop} size="sm" plated={false} />
            <span>{script.text || produce.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function MandiPicker() {
  const { mandiId, setMandiId } = useToolSelection();
  const { data } = useQuery({
    queryKey: ['farmer-mandis'],
    queryFn: () => farmerApi.listMandis(),
    staleTime: Infinity,
  });

  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
        Mandi
      </span>
      <select
        value={mandiId}
        onChange={(event) => setMandiId(event.target.value)}
        className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold text-[var(--farm-ink)]"
      >
        {(data?.mandis ?? []).map((m) => (
          <option key={m.mandi_id} value={m.mandi_id}>
            {m.mandi_name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function QuantityPicker() {
  const { quantityQuintals, setQuantityQuintals } = useToolSelection();
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
        Quantity (quintals)
      </span>
      <input
        type="number"
        min={0.1}
        step={0.5}
        value={quantityQuintals}
        onChange={(event) => setQuantityQuintals(Math.max(0.1, Number(event.target.value) || 0))}
        className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold tabular-nums text-[var(--farm-ink)]"
      />
    </label>
  );
}

export function PhonePicker({ label = 'Your phone number' }: { label?: string }) {
  const { phone, setPhone } = useToolSelection();
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-[var(--farm-ink-faint)]">
        {label}
      </span>
      <input
        type="tel"
        inputMode="tel"
        value={phone}
        onChange={(event) => setPhone(event.target.value)}
        placeholder="98765 43210"
        className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-base font-semibold tabular-nums text-[var(--farm-ink)] placeholder:font-normal placeholder:text-[var(--farm-ink-faint)]"
      />
    </label>
  );
}
