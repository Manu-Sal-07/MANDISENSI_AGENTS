/**
 * Trader feature API client.
 *
 * One typed method per endpoint in `api/trader_router.py` — see
 * `mandisense_ai/trader/` for what each feature computes and why. Same
 * convention as `farmerApi.ts`: every feature can return a refusal status
 * instead of data (UNAVAILABLE, INSUFFICIENT_HISTORY,
 * INSUFFICIENT_EVIDENCE, ...), which is the honest answer for a series this
 * system cannot yet speak to, not a network error — callers must check
 * `status` before reading any numeric field.
 */

import { apiClient } from './api';

// ── Spread scanner ────────────────────────────────────────────────────────

export interface SpreadOpportunity {
  buy_mandi: string;
  buy_mandi_name: string;
  sell_mandi: string;
  sell_mandi_name: string;
  buy_price: number;
  sell_price: number;
  buy_price_date: string;
  sell_price_date: string;
  distance_km: number;
  trip_days: number;
  transport_cost_per_quintal: number;
  vehicle: string;
  vehicles_needed: number | null;
  today_net_per_quintal: number;
  expected_net_on_arrival_per_quintal: number;
  expected_net_on_arrival_pct: number | null;
  expected_net_total: number;
  structural_net_per_quintal: number | null;
  half_life_days: number | null;
  model: 'ar1_mean_reversion' | 'random_walk' | 'no_history';
  history_prints: number;
  closure: { episodes: number; closed: number; rate: number | null } | null;
  survives_trip: boolean;
}

export interface SpreadScanResult {
  status: 'OK' | 'UNAVAILABLE';
  commodity?: string;
  reason?: string;
  as_of?: string | null;
  mandis_compared?: number;
  stale_mandis?: string[];
  quantity_quintals?: number;
  assumptions?: {
    transport_model: string;
    vehicles: Array<{ capacity_quintals: number; rate_per_km: number; label: string }>;
    average_truck_speed_kmph: number;
    handling_days: number;
    history_days: number;
  };
  opportunities?: SpreadOpportunity[];
  survivors?: number;
  vanishing?: number;
}

// ── Volatility & regimes ──────────────────────────────────────────────────

export interface VolatilityWindow {
  current_daily_pct: number | null;
  percentile: number | null;
  median_daily_pct: number | null;
  p90_daily_pct: number | null;
}

export interface VolatilityResult {
  status: 'OK' | 'INSUFFICIENT_HISTORY';
  commodity?: string;
  mandi_id?: string;
  reason?: string;
  as_of?: string;
  prints?: number;
  windows?: Record<'10' | '20' | '60', VolatilityWindow>;
  current_regime?: 'CALM' | 'NORMAL' | 'TURBULENT' | null;
  regime_share?: { CALM: number; NORMAL: number; TURBULENT: number };
  regime_segments?: Array<{ regime: string; start: string; end: string; prints: number }>;
  series?: Array<{ date: string; price: number; vol_20_daily_pct: number; regime: string }>;
}

// ── Historical analogs ─────────────────────────────────────────────────────

export interface AnalogEntry {
  start: string;
  end: string;
  distance: number;
  similarity: number;
  forward_return_pct: number;
  path: number[];
}

export interface AnalogsResult {
  status: 'OK' | 'INSUFFICIENT_HISTORY' | 'INSUFFICIENT_EVIDENCE';
  commodity?: string;
  mandi_id?: string;
  reason?: string;
  as_of?: string;
  window_prints?: number;
  horizon_days?: number;
  current_path?: number[];
  analogs?: AnalogEntry[];
  outcome?: { n: number; share_up: number; median_pct: number; p10_pct: number; p90_pct: number };
  baseline?: { n: number; share_up: number; median_pct: number };
  disclaimer?: string;
}

// ── Scenarios ──────────────────────────────────────────────────────────────

export interface ScenarioResult {
  status: 'OK' | 'INSUFFICIENT_HISTORY' | 'INSUFFICIENT_EVIDENCE' | 'UNAVAILABLE' | 'ERROR';
  commodity?: string;
  mandi_id?: string;
  scenario?: string;
  label?: string;
  definition?: string;
  horizon_days?: number;
  reason?: string;
  disclaimer?: string;
  baseline?: { n: number; share_down: number; median_pct: number };
  as_of?: string;
  condition_active_now?: boolean;
  episodes?: number;
  outcome?: { share_down: number; median_pct: number; p10_pct: number; p90_pct: number; mean_pct: number };
  edge_vs_baseline_pct?: number;
  recent_episodes?: Array<{ date: string; price: number; forward_return_pct: number }>;
}

export interface AllScenariosResult {
  status: 'OK';
  commodity: string;
  mandi_id: string;
  horizon_days: number;
  scenarios: ScenarioResult[];
}

// ── Forward price ──────────────────────────────────────────────────────────

export interface ForwardPriceResult {
  status: 'OK' | 'UNAVAILABLE' | 'UNSUITABLE' | 'ERROR';
  commodity?: string;
  mandi_id?: string;
  reason?: string;
  horizon_days?: number;
  quantity_quintals?: number;
  basis?: 'calibrated_forecast' | 'historical_returns';
  basis_sample_size?: number | null;
  base_price?: number;
  base_date?: string;
  price_age_days?: number | null;
  expected_price_at_delivery?: number;
  delivery_price_range_90?: [number, number];
  farmer_floor?: number;
  trader_ceiling?: number;
  risk_premium_per_quintal?: number;
  spoilage_over_horizon_pct?: number;
  deal_possible?: boolean;
  fair_price?: number;
  farmer_surplus_per_quintal?: number;
  trader_surplus_per_quintal?: number;
  farmer_surplus_total?: number;
  trader_surplus_total?: number;
  contract_value?: number;
  caveat?: string;
}

// ── Position book ──────────────────────────────────────────────────────────

export type PositionSide = 'LONG' | 'SHORT';

export interface Position {
  id: string;
  book_id: string;
  commodity: string;
  mandi_id: string;
  quantity_quintals: number;
  avg_cost: number | null;
  side: PositionSide;
  created_at: string;
}

export interface PricedPosition extends Position {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  mark_price?: number;
  mark_date?: string;
  price_age_days?: number | null;
  exposure?: number;
  unrealised_pnl?: number | null;
  pnl_p05?: number;
  pnl_p50?: number;
  pnl_p95?: number;
  basis?: string;
  sample_size?: number | null;
}

export interface BookRiskResult {
  status: 'OK' | 'EMPTY' | 'UNAVAILABLE';
  book_id?: string;
  reason?: string;
  horizon_days?: number;
  gross_exposure?: number;
  net_exposure?: number;
  by_commodity?: Record<string, number>;
  portfolio?: {
    method: 'historical_simulation_joint' | 'sum_of_individual_worst_cases';
    shared_dates: number;
    worst_case_95: number;
    expected_shortfall_95: number | null;
    median_pnl: number;
    best_case_95: number;
    note?: string;
  };
  basis?: string[];
  positions?: PricedPosition[];
  unpriced?: PricedPosition[];
}

export const traderApi = {
  spreads: (commodity: string, quantityQuintals = 20, maxResults = 12, transportRateOverride?: number) =>
    apiClient<SpreadScanResult>(`/v1/trader/spreads/${commodity}`, {
      params: {
        quantity_quintals: String(quantityQuintals),
        max_results: String(maxResults),
        ...(transportRateOverride ? { transport_rate_override: String(transportRateOverride) } : {}),
      },
    }),

  volatility: (commodity: string, mandiId: string, timelinePoints = 180) =>
    apiClient<VolatilityResult>(`/v1/trader/volatility/${commodity}/${mandiId}`, {
      params: { timeline_points: String(timelinePoints) },
    }),

  analogs: (commodity: string, mandiId: string, window = 30, horizonDays = 7, topK = 15) =>
    apiClient<AnalogsResult>(`/v1/trader/analogs/${commodity}/${mandiId}`, {
      params: { window: String(window), horizon_days: String(horizonDays), top_k: String(topK) },
    }),

  scenarios: (commodity: string, mandiId: string, horizonDays = 5) =>
    apiClient<AllScenariosResult>(`/v1/trader/scenarios/${commodity}/${mandiId}`, {
      params: { horizon_days: String(horizonDays) },
    }),

  forwardPrice: (commodity: string, mandiId: string, horizonDays = 7, quantityQuintals = 10) =>
    apiClient<ForwardPriceResult>(`/v1/trader/forward-price/${commodity}/${mandiId}`, {
      params: { horizon_days: String(horizonDays), quantity_quintals: String(quantityQuintals) },
    }),

  addPosition: (
    bookId: string,
    commodity: string,
    mandiId: string,
    quantityQuintals: number,
    avgCost?: number,
    side: PositionSide = 'LONG'
  ) =>
    apiClient<{ status: string; position: Position }>('/v1/trader/positions', {
      method: 'POST',
      body: JSON.stringify({
        book_id: bookId, commodity, mandi_id: mandiId,
        quantity_quintals: quantityQuintals, avg_cost: avgCost, side,
      }),
    }),

  listPositions: (bookId: string) =>
    apiClient<{ book_id: string; positions: Position[] }>('/v1/trader/positions', {
      params: { book_id: bookId },
    }),

  deletePosition: (bookId: string, positionId: string) =>
    apiClient<{ status: string }>(`/v1/trader/positions/${positionId}`, {
      method: 'DELETE',
      params: { book_id: bookId },
    }),

  assessRisk: (bookId: string, horizonDays = 5) =>
    apiClient<BookRiskResult>('/v1/trader/positions/risk', {
      params: { book_id: bookId, horizon_days: String(horizonDays) },
    }),
};
