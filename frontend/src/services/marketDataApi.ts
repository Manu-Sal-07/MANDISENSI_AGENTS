/**
 * Client for the TraderOS commodity chart backend (/v1/market-data/*).
 * Deliberately separate from the cognition/copilot data layer — this is
 * pure observed price + volume history, not model forecasts.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type Timeframe = 'week' | 'month' | 'year';

export const COMMODITIES = ['tomato', 'onion', 'potato', 'garlic', 'ginger'] as const;
export type Commodity = (typeof COMMODITIES)[number];

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type CandlesResponse = {
  commodity: string;
  mandi_id: string;
  timeframe: Timeframe;
  candles: Candle[];
};

export type MarketsResponse = {
  commodities: string[];
  markets: Record<string, string[]>;
};

export type MonthStat = { month: string; avg_price: number };
export type VolumeMonthStat = { month: string; total_arrivals: number };

export type SummaryResponse = {
  commodity: string;
  mandi_id: string;
  as_of: string;
  current_price: number;
  week_change_pct: number | null;
  month_change_pct: number | null;
  year_change_pct: number | null;
  year_over_year_pct: number | null;
  highest_month: MonthStat;
  lowest_month: MonthStat;
  highest_volume_month: VolumeMonthStat | null;
  data_points: number;
  history_start: string;
};

export type ComparisonPoint = { time: string; value: number };

export type CompareResponse = {
  mandi_id: string;
  timeframe: Timeframe;
  series: Record<string, ComparisonPoint[]>;
  ranking: { commodity: string; change_pct: number }[];
};

export type SyncResult = {
  status: string;
  results: Array<{ commodity: string; status: string; date?: string; rows_added?: number; error?: string }>;
};

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const marketDataApi = {
  getMarkets: (signal?: AbortSignal) => getJson<MarketsResponse>('/v1/market-data/markets', signal),

  getCandles: (commodity: string, mandiId: string, timeframe: Timeframe, signal?: AbortSignal) =>
    getJson<CandlesResponse>(
      `/v1/market-data/candles/${encodeURIComponent(commodity)}/${encodeURIComponent(mandiId)}?timeframe=${timeframe}`,
      signal
    ),

  getSummary: (commodity: string, mandiId: string, signal?: AbortSignal) =>
    getJson<SummaryResponse>(
      `/v1/market-data/summary/${encodeURIComponent(commodity)}/${encodeURIComponent(mandiId)}`,
      signal
    ),

  getComparison: (mandiId: string, timeframe: Timeframe, commodities?: string[], signal?: AbortSignal) => {
    const query = new URLSearchParams({ mandi_id: mandiId, timeframe });
    if (commodities?.length) query.set('commodities', commodities.join(','));
    return getJson<CompareResponse>(`/v1/market-data/compare?${query.toString()}`, signal);
  },

  triggerSync: async (): Promise<SyncResult> => {
    const res = await fetch(`${API_BASE_URL}/v1/market-data/sync`, { method: 'POST' });
    if (!res.ok) throw new Error(`Sync failed: ${res.status}`);
    return res.json();
  },
};
