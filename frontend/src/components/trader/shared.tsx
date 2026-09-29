'use client';

import React from 'react';
import { Loader2, TriangleAlert } from 'lucide-react';

export const COMMODITIES = ['tomato', 'onion', 'potato', 'garlic', 'ginger', 'dry_chillies'];

export const formatRupees = (value?: number | null): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;
};

export const formatPct = (value?: number | null, digits = 1): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}%`;
};

export const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' });
  } catch {
    return value;
  }
};

/**
 * The shared card shell for every trader tool panel — same border,
 * elevation and header rhythm as the rest of the analyst surface
 * (`.glass-panel` / `surface-*` tokens in globals.css), so these new panels
 * read as native to Market Explorer and the Command Center rather than a
 * bolted-on second design system.
 */
export function ToolCard({
  title,
  subtitle,
  icon,
  accent = 'var(--accent)',
  children,
}: {
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-panel rounded-2xl border border-border p-5">
      <div className="flex items-start gap-3">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          style={{ background: `${accent}1f`, color: accent }}
        >
          {icon}
        </span>
        <div className="min-w-0">
          <h3 className="font-display text-sm font-bold tracking-tight text-foreground">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-neutral-signal">{subtitle}</p>}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

export function LoadingRow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-neutral-signal">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function RefusalNotice({ reason }: { reason?: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3.5 py-3">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
      <div>
        <p className="text-xs font-bold text-amber-500">Not enough data yet</p>
        {reason && <p className="mt-0.5 text-xs leading-relaxed text-amber-500/80">{reason}</p>}
      </div>
    </div>
  );
}

export function CommodityPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold capitalize text-foreground outline-none focus:ring-2 focus:ring-accent/30"
    >
      {COMMODITIES.map((c) => (
        <option key={c} value={c} className="capitalize">
          {c.replace('_', ' ')}
        </option>
      ))}
    </select>
  );
}

export function MandiPicker({
  value,
  onChange,
  mandis,
}: {
  value: string;
  onChange: (v: string) => void;
  mandis: Array<{ mandi_id: string; mandi_name: string }>;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground outline-none focus:ring-2 focus:ring-accent/30"
    >
      {mandis.map((m) => (
        <option key={m.mandi_id} value={m.mandi_id}>
          {m.mandi_name}
        </option>
      ))}
    </select>
  );
}
