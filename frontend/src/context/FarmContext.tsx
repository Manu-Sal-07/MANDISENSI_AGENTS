'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { farmerApi, type CatalogDistrict, type CropId, type FarmCatalog } from '@/services/farmerApi';

/**
 * What the farmer is looking at: a district, a crop, and (for the sale
 * planner) a mandi and a load size. Persisted on the device so the app opens
 * where it was left.
 *
 * The list of places and crops comes from the server's catalog, which is built
 * from the real data, so the app can never offer a district or crop that has
 * no prices behind it.
 */

interface Selection {
  district: string;
  crop: CropId;
  mandi: string | null;
  quantity: number;
}

interface FarmContextValue extends Selection {
  catalog: FarmCatalog | undefined;
  catalogLoading: boolean;
  catalogError: boolean;
  districtInfo: CatalogDistrict | undefined;
  setDistrict: (id: string) => void;
  setCrop: (crop: CropId) => void;
  setMandi: (id: string) => void;
  setQuantity: (qty: number) => void;
}

const STORAGE_KEY = 'mandisense-farm-selection-v2';
const DEFAULTS: Selection = { district: 'kolar', crop: 'tomato', mandi: null, quantity: 10 };

const FarmCtx = createContext<FarmContextValue | null>(null);

export function FarmProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelection] = useState<Selection>(DEFAULTS);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setSelection((prev) => ({ ...prev, ...JSON.parse(raw) }));
    } catch {
      // Private browsing: start from the defaults.
    }
  }, []);

  const { data: catalog, isLoading, isError } = useQuery({
    queryKey: ['farm-catalog'],
    queryFn: () => farmerApi.catalog(),
    staleTime: 10 * 60 * 1000,
  });

  const persist = useCallback((next: Selection) => {
    setSelection(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Losing the preference is fine.
    }
  }, []);

  const districtInfo = catalog?.districts.find((d) => d.id === selection.district);

  // If the saved district or crop is not one the data covers, fall back to the
  // first that is, rather than showing an empty screen.
  useEffect(() => {
    if (!catalog) return;
    const d = catalog.districts.find((x) => x.id === selection.district) ?? catalog.districts[0];
    if (!d) return;
    const crop = d.crops.some((c) => c.crop === selection.crop) ? selection.crop : d.crops[0].crop;
    if (d.id !== selection.district || crop !== selection.crop) persist({ ...selection, district: d.id, crop, mandi: null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog]);

  const value = useMemo<FarmContextValue>(
    () => ({
      ...selection,
      catalog,
      catalogLoading: isLoading,
      catalogError: isError,
      districtInfo,
      setDistrict: (id) => {
        const d = catalog?.districts.find((x) => x.id === id);
        const crop = d?.crops.some((c) => c.crop === selection.crop) ? selection.crop : d?.crops[0]?.crop ?? selection.crop;
        persist({ ...selection, district: id, crop, mandi: null });
      },
      setCrop: (crop) => persist({ ...selection, crop }),
      setMandi: (mandi) => persist({ ...selection, mandi }),
      setQuantity: (quantity) => persist({ ...selection, quantity }),
    }),
    [selection, catalog, isLoading, isError, districtInfo, persist]
  );

  return <FarmCtx.Provider value={value}>{children}</FarmCtx.Provider>;
}

export function useFarm(): FarmContextValue {
  const ctx = useContext(FarmCtx);
  if (!ctx) throw new Error('useFarm must be used within a FarmProvider');
  return ctx;
}
