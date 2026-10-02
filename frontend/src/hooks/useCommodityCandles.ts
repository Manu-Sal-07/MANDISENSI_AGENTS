'use client';

import { useEffect, useRef, useState } from 'react';
import {
  marketDataApi,
  type Candle,
  type CompareResponse,
  type MarketsResponse,
  type SummaryResponse,
  type Timeframe,
} from '@/services/marketDataApi';

// Real historical data changes at most once a day (the live sync job), so a
// short TTL is enough to stay fresh without re-fetching on every render —
// unlike marketCache.ts elsewhere, which caches forever for the tab's life.
const TTL_MS = 5 * 60 * 1000;

type CacheEntry<T> = { data: T; expiresAt: number };
const cache = new Map<string, CacheEntry<unknown>>();

function readCache<T>(key: string): T | null {
  const hit = cache.get(key);
  if (!hit || hit.expiresAt < Date.now()) return null;
  return hit.data as T;
}

function writeCache<T>(key: string, data: T) {
  cache.set(key, { data, expiresAt: Date.now() + TTL_MS });
}

export function useMarketList() {
  const [markets, setMarkets] = useState<MarketsResponse | null>(() => readCache('markets'));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (readCache<MarketsResponse>('markets')) return;
    const controller = new AbortController();
    marketDataApi
      .getMarkets(controller.signal)
      .then((data) => {
        writeCache('markets', data);
        setMarkets(data);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message);
      });
    return () => controller.abort();
  }, []);

  return { markets, error };
}

export function useCommodityCandles(commodity: string, mandiId: string | null, timeframe: Timeframe) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!mandiId) return;
    const key = `candles|${commodity}|${mandiId}|${timeframe}`;
    const cached = readCache<{ candles: Candle[]; summary: SummaryResponse }>(key);

    if (cached) {
      setCandles(cached.candles);
      setSummary(cached.summary);
      setLoading(false);
      setError(null);
      return;
    }

    const myRequest = ++requestId.current;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      marketDataApi.getCandles(commodity, mandiId, timeframe, controller.signal),
      marketDataApi.getSummary(commodity, mandiId, controller.signal),
    ])
      .then(([candlesRes, summaryRes]) => {
        if (myRequest !== requestId.current) return; // stale response from a superseded request
        writeCache(key, { candles: candlesRes.candles, summary: summaryRes });
        setCandles(candlesRes.candles);
        setSummary(summaryRes);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError' || myRequest !== requestId.current) return;
        setError(err.message || 'Failed to load market data');
        setLoading(false);
      });

    return () => controller.abort();
  }, [commodity, mandiId, timeframe]);

  return { candles, summary, loading, error };
}

export function useCommodityComparison(mandiId: string | null, timeframe: Timeframe) {
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!mandiId) return;
    const key = `compare|${mandiId}|${timeframe}`;
    const cached = readCache<CompareResponse>(key);
    if (cached) {
      setComparison(cached);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    marketDataApi
      .getComparison(mandiId, timeframe, undefined, controller.signal)
      .then((data) => {
        writeCache(key, data);
        setComparison(data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Failed to load comparison data');
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [mandiId, timeframe]);

  return { comparison, loading, error };
}
