'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export interface ToolSelection {
  commodity: string;
  mandiId: string;
  quantityQuintals: number;
  phone: string;
}

interface ToolContextValue extends ToolSelection {
  setCommodity: (commodity: string) => void;
  setMandiId: (mandiId: string) => void;
  setQuantityQuintals: (qty: number) => void;
  setPhone: (phone: string) => void;
}

const STORAGE_KEY = 'mandisense-tool-selection';

const DEFAULTS: ToolSelection = {
  commodity: 'tomato',
  mandiId: 'kolar_apmc',
  quantityQuintals: 10,
  phone: '',
};

const ToolCtx = createContext<ToolContextValue | null>(null);

/**
 * The crop, mandi, quantity and phone number a farmer is working with,
 * shared across every tool panel and persisted between visits.
 *
 * Every feature in `farmer_router.py` takes some subset of these four
 * inputs. Without a shared place to hold them, opening Fair Price Check
 * for tomato at Kolar and then Hold-or-Rot would ask the same two
 * questions again — a second tax on exactly the audience this surface
 * exists to save taps for.
 */
export function ToolProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelection] = useState<ToolSelection>(DEFAULTS);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setSelection((prev) => ({ ...prev, ...JSON.parse(raw) }));
    } catch {
      // Fall back to defaults silently.
    }
  }, []);

  const persist = useCallback((next: ToolSelection) => {
    setSelection(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Losing the preference is fine; crashing is not.
    }
  }, []);

  const value = useMemo<ToolContextValue>(
    () => ({
      ...selection,
      setCommodity: (commodity) => persist({ ...selection, commodity }),
      setMandiId: (mandiId) => persist({ ...selection, mandiId }),
      setQuantityQuintals: (quantityQuintals) => persist({ ...selection, quantityQuintals }),
      setPhone: (phone) => persist({ ...selection, phone }),
    }),
    [selection, persist]
  );

  return <ToolCtx.Provider value={value}>{children}</ToolCtx.Provider>;
}

export function useToolSelection(): ToolContextValue {
  const ctx = useContext(ToolCtx);
  if (!ctx) throw new Error('useToolSelection must be used within a ToolProvider');
  return ctx;
}
