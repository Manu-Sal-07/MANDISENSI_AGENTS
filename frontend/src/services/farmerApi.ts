/**
 * Farmer feature API client.
 *
 * One typed method per endpoint in `api/farmer_router.py`. Kept as its own
 * file rather than appended to `api.ts` because these are a self-contained
 * feature set with their own response shapes; splitting them keeps
 * `api.ts` from becoming a dumping ground as more farmer tools are added.
 *
 * Every feature here can return `status: "UNAVAILABLE"` (or a
 * feature-specific refusal status like "INSUFFICIENT_HISTORY") instead of
 * data. That is not a network error — it is the honest answer for a series
 * this system cannot yet speak to — so callers must render `status` before
 * assuming any numeric field is present, exactly as `ForecastPanel` already
 * does for the forecast curve itself.
 */

import { apiClient } from './api';

// ── Fair Price Check ─────────────────────────────────────────────────────

export interface FairPriceResult {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  offered_price?: number;
  verdict?: 'well_below' | 'below' | 'fair' | 'above' | 'well_above';
  message?: { en: string; kn: string };
  observed?: {
    as_of_date: string;
    modal_price: number;
    range_low: number;
    range_high: number;
    verdict: string;
  };
  forecast?: {
    horizon_days: number;
    target_date: string | null;
    range_low: number;
    range_high: number;
    verdict: string;
  } | null;
  quantity_quintals?: number;
  offered_total?: number;
  typical_total?: number;
  difference?: number;
}

// ── My Harvest in Rupees ─────────────────────────────────────────────────

export interface HarvestDay {
  horizon_days: number | null;
  target_date: string | null;
  label: string;
  status: string;
  reason?: string;
  expected_total: number | null;
  range_low: number | null;
  range_high: number | null;
  price_per_quintal: number | null;
  decision?: string | null;
  interval_source?: string | null;
}

export interface HarvestPlan {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  quantity_quintals?: number;
  as_of_date?: string | null;
  days: HarvestDay[];
  best_day?: string | null;
  best_day_horizon?: number | null;
  safest_day?: string | null;
}

// ── Hold or Rot ───────────────────────────────────────────────────────────

export interface HoldOrRotOption {
  horizon_days: number;
  target_date: string | null;
  price_per_quintal: number;
  gross_value: number;
  spoilage_cost: number;
  net_value: number;
  gain_vs_sell_today: number;
  decision?: string | null;
  probability_of_decline?: number | null;
}

export interface HoldOrRotResult {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  quantity_quintals?: number;
  shelf_profile: { shelf_life_days: number; daily_loss_pct?: number; category: string };
  sell_today_value?: number;
  options?: HoldOrRotOption[];
  recommendation?: 'HOLD' | 'SELL';
  best_option?: HoldOrRotOption | null;
  reasoning?: string;
}

// ── This Time Last Year ──────────────────────────────────────────────────

export interface SeasonalMemoryResult {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  as_of_date?: string;
  current_price?: number;
  last_year?: { date: string; price: number; change_pct: number | null } | null;
  seasonal_norm?: { median_price: number; reference_years: number; deviation_pct: number } | null;
}

// ── Where to Sell ─────────────────────────────────────────────────────────

export interface MandiComparisonRow {
  mandi_id: string;
  mandi_name: string;
  distance_km: number;
  as_of_date: string;
  gross_price_per_quintal: number;
  transport_cost_per_quintal: number;
  net_price_per_quintal: number;
  net_total: number;
}

export interface WhereToSellResult {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  commodity?: string;
  quantity_quintals?: number;
  transport_rate_per_quintal_per_km?: number;
  mandis?: MandiComparisonRow[];
  best_mandi_id?: string;
  best_over_worst?: number;
}

// ── Supply Flood Warning ──────────────────────────────────────────────────

export interface SupplySignalResult {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE' | 'INSUFFICIENT_HISTORY';
  reason?: string;
  signal?: 'FLOOD' | 'DROUGHT' | 'NORMAL';
  latest_arrivals?: number;
  baseline_arrivals?: number;
  deviation_pct?: number;
  as_of_date?: string;
  data_age_days?: number;
  is_live_reading?: boolean;
  historical_note?: string | null;
}

// ── Track Record ──────────────────────────────────────────────────────────

export interface TrackRecordResult {
  status: 'OK' | 'NO_RECORDS' | 'INSUFFICIENT_EVIDENCE' | 'ERROR';
  scored: number;
  required?: number;
  note?: string;
  horizon_days?: number | null;
  directional_accuracy?: number | null;
  coverage_90?: number | null;
  coverage_50?: number | null;
  decision_precision?: number | null;
  decision_calls?: number;
  decision_coverage?: number;
  commodity?: string;
  mandi_id?: string;
}

// ── What to Plant Next Season ─────────────────────────────────────────────

export interface CropPlanningResult {
  status: 'OK' | 'UNAVAILABLE' | 'ERROR';
  reason?: string;
  mandi_id?: string;
  target_month?: number;
  disclaimer?: string;
  crops?: Array<{
    commodity: string;
    years_observed: number;
    avg_deviation_from_own_yearly_mean_pct: number;
    consistency: number | null;
  }>;
}

// ── Alerts ────────────────────────────────────────────────────────────────

export type AlertType = 'PRICE_ABOVE' | 'PRICE_BELOW' | 'DECISION_SELL' | 'DECISION_HOLD';

export interface PriceAlert {
  id: string;
  phone: string;
  commodity: string;
  mandi_id: string;
  alert_type: AlertType;
  threshold: number | null;
  created_at: string;
  active: boolean;
  last_triggered_at: string | null;
}

// ── Truck Sharing ─────────────────────────────────────────────────────────

export interface TruckTrip {
  id: string;
  mandi_id: string;
  mandi_name: string;
  travel_date: string;
  total_capacity_quintals: number;
  claimed_quintals: number;
  posted_by_phone: string;
  posted_by_name: string;
  created_at: string;
  status: 'OPEN' | 'FULL';
  claims: Array<{ phone: string; name: string; quantity_quintals: number; joined_at: string }>;
}


// ── The farmer app's read model (mandisense_ai/farmer/dashboard.py) ────────

export type CropId = 'tomato' | 'onion' | 'potato' | 'ginger' | 'garlic';

export interface PlaceNames {
  en: string;
  kn: string;
  hi: string;
}

export interface CatalogDistrict {
  id: string;
  name: string;
  name_kn: string;
  name_hi: string;
  lat: number;
  lon: number;
  mandis: Array<{ id: string; name: string; name_kn: string; name_hi: string }>;
  crops: Array<{ crop: CropId; has_call: boolean }>;
}

export interface FarmCatalog {
  data_through: string | null;
  forecast_as_of: string | null;
  crops: Array<{ id: CropId; name_kn: string }>;
  districts: CatalogDistrict[];
  served_horizons: number[];
}

export type FarmCall =
  | { type: 'NONE' | 'RANGE_ONLY'; reason?: string }
  | { type: 'ABSTAINED'; decision: 'WAIT'; horizon: number; expected_change_pct: number | null }
  | {
      type: 'ADVISED';
      decision: 'SELL' | 'HOLD';
      horizon: number;
      date: string | null;
      expected_change_pct: number | null;
      confidence: number | null;
    };

export interface OverviewCrop {
  crop: CropId;
  price: number;
  date: string;
  d7: number | null;
  d1: number | null;
  spark: number[];
  call: FarmCall;
}

export interface FarmOverview {
  district: string;
  district_name: PlaceNames | null;
  crops: OverviewCrop[];
}

export interface ForecastPoint {
  horizon: number;
  date: string | null;
  price: number | null;
  p05: number | null;
  p25: number | null;
  p75: number | null;
  p95: number | null;
  change_pct: number | null;
  decision: string | null;
  p_decline: number | null;
}

export interface MandiToday {
  id: string;
  name: string;
  name_kn: string;
  name_hi: string;
  district: string;
  in_district: boolean;
  date: string;
  price: number;
  min: number;
  max: number;
  arrivals: number;
}

export interface FarmReason {
  code:
    | 'price_up_week'
    | 'price_down_week'
    | 'arrivals_high'
    | 'arrivals_low'
    | 'above_last_year'
    | 'below_last_year'
    | 'model_expects_up'
    | 'model_expects_down'
    | 'spoils_fast'
    | 'neighbours_dearer'
    | 'neighbours_cheaper';
  value: number | null;
  days?: number;
  weeks?: number;
}

export interface GapNote {
  gap_pct: number;
  direction: 'neighbours_dearer' | 'neighbours_cheaper';
  half_life_weeks: number;
  pairs: number;
}

export interface FarmBoard {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  district: string;
  district_name: PlaceNames | null;
  crop: CropId;
  price: { value: number; date: string; age_days: number; arrivals: number | null };
  changes: { d1: number | null; d7: number | null; d30: number | null };
  history: Array<{ d: string; p: number; a: number | null }>;
  history_last_year: Array<{ d: string; p: number }>;
  forecast: ForecastPoint[];
  call: FarmCall;
  reasons: FarmReason[];
  supply: SupplySignalResult | null;
  seasonal: SeasonalMemoryResult | null;
  mandis: MandiToday[];
  shelf: { days: number; daily_loss_pct: number; category: string };
  accuracy: { forecasts?: number; skill_vs_no_change?: number; direction_right?: number; serves_call?: boolean };
  gap: GapNote | null;
}

export interface MandiPage {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  mandi?: { id: string; name: string; name_kn: string; name_hi: string; district: string };
  crops?: Array<{
    crop: CropId;
    date: string;
    price: number;
    min: number;
    max: number;
    arrivals: number;
    d7: number | null;
    days_reported: number;
  }>;
}

export interface SellPlanOption {
  choice: 'sell_today' | 'travel' | 'wait';
  mandi_id: string;
  mandi_name: string;
  mandi_name_kn: string;
  mandi_name_hi: string;
  target_date: string | null;
  price_per_quintal: number;
  transport_cost_per_quintal: number;
  total: number;
  distance_km?: number;
  horizon?: number;
  spoilage_pct?: number;
  range_low?: number | null;
  range_high?: number | null;
  gap_half_life_weeks?: number | null;
  typical_arrivals_tonnes?: number;
  thin_for_load?: boolean;
}

export interface SellPlanResult {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop?: CropId;
  quantity_quintals?: number;
  baseline_total?: number;
  best?: SellPlanOption['choice'];
  gain_vs_baseline?: number;
  options?: SellPlanOption[];
  call?: FarmCall;
  transport_rate_per_quintal_per_km?: number;
  shelf?: { days: number; daily_loss_pct: number; category: string };
}

export interface SeriesQuality {
  forecasts: number;
  skill_vs_no_change: number;
  direction_right: number | null;
  base_rate_price_fell: number;
  skill_latest_fold: number | null;
  serves_call: boolean;
}

export interface AccuracyReport {
  available: boolean;
  generated_at?: string;
  data?: { source: string; series: number; rows: number; from: string; to: string };
  method?: string;
  served_horizons?: number[];
  overall?: { forecasts: number; skill_vs_no_change: number; direction_right: number | null; base_rate_price_fell: number };
  last_fold_window?: [string, string] | null;
  horizons?: Record<string, {
    promoted: boolean;
    skill_vs_no_change: number | null;
    direction_right?: number | null;
    coverage_90?: number | null;
    mean_band_width_pct?: number | null;
    decision?: { threshold: number; precision_sell: number; precision_hold: number; coverage: number };
  }>;
  by_crop?: Record<string, { forecasts: number; skill_vs_no_change: number; direction_right: number | null }>;
  by_district?: Record<string, { forecasts: number; skill_vs_no_change: number; direction_right: number | null }>;
  series_quality?: Record<string, SeriesQuality>;
  call_rule?: { min_skill: number; min_direction_right: number; also_required: string };
}

// ── Price on a Date (verification for the "My Money" ledger) ──────────────

export interface PriceOnDateResult {
  commodity: string;
  mandi_id: string;
  status: 'OK' | 'UNAVAILABLE' | 'ERROR';
  reason?: string;
  requested_date?: string;
  matched_date?: string;
  modal_price?: number;
  gap_days?: number;
}

// ── Reference ──────────────────────────────────────────────────────────────

export interface MandiReference {
  mandi_id: string;
  mandi_name: string;
  lat: number;
  lon: number;
}

export interface NearestMandi {
  mandi_id: string;
  mandi_name: string;
  distance_km: number;
}

export const farmerApi = {
  fairPriceCheck: (commodity: string, mandiId: string, offeredPrice: number, quantityQuintals?: number) =>
    apiClient<FairPriceResult>(`/v1/farmer/fair-price/${commodity}/${mandiId}`, {
      params: {
        offered_price: String(offeredPrice),
        ...(quantityQuintals ? { quantity_quintals: String(quantityQuintals) } : {}),
      },
    }),

  harvestPlan: (commodity: string, mandiId: string, quantityQuintals: number) =>
    apiClient<HarvestPlan>(`/v1/farmer/harvest/${commodity}/${mandiId}`, {
      params: { quantity_quintals: String(quantityQuintals) },
    }),

  holdOrSell: (commodity: string, mandiId: string, quantityQuintals: number = 1) =>
    apiClient<HoldOrRotResult>(`/v1/farmer/hold-or-sell/${commodity}/${mandiId}`, {
      params: { quantity_quintals: String(quantityQuintals) },
    }),

  seasonalMemory: (commodity: string, mandiId: string) =>
    apiClient<SeasonalMemoryResult>(`/v1/farmer/seasonal-memory/${commodity}/${mandiId}`),

  whereToSell: (
    commodity: string,
    origin: { mandiId?: string; lat?: number; lon?: number },
    quantityQuintals: number = 1
  ) =>
    apiClient<WhereToSellResult>(`/v1/farmer/where-to-sell/${commodity}`, {
      params: {
        ...(origin.mandiId ? { origin_mandi_id: origin.mandiId } : {}),
        ...(origin.lat !== undefined ? { origin_lat: String(origin.lat) } : {}),
        ...(origin.lon !== undefined ? { origin_lon: String(origin.lon) } : {}),
        quantity_quintals: String(quantityQuintals),
      },
    }),

  supplySignal: (commodity: string, mandiId: string) =>
    apiClient<SupplySignalResult>(`/v1/farmer/supply-signal/${commodity}/${mandiId}`),

  trackRecord: (commodity: string, mandiId: string, horizonDays?: number) =>
    apiClient<TrackRecordResult>(`/v1/farmer/track-record/${commodity}/${mandiId}`, {
      params: horizonDays ? { horizon_days: String(horizonDays) } : {},
    }),

  cropPlanning: (mandiId: string, targetMonth: number) =>
    apiClient<CropPlanningResult>(`/v1/farmer/crop-planning/${mandiId}`, {
      params: { target_month: String(targetMonth) },
    }),

  createAlert: (phone: string, commodity: string, mandiId: string, alertType: AlertType, threshold?: number) =>
    apiClient<{ status: string; alert: PriceAlert }>('/v1/farmer/alerts', {
      method: 'POST',
      body: JSON.stringify({ phone, commodity, mandi_id: mandiId, alert_type: alertType, threshold }),
    }),

  listAlerts: (phone: string) =>
    apiClient<{ phone: string; alerts: PriceAlert[] }>('/v1/farmer/alerts', { params: { phone } }),

  deleteAlert: (phone: string, alertId: string) =>
    apiClient<{ status: string }>(`/v1/farmer/alerts/${alertId}`, { method: 'DELETE', params: { phone } }),

  postTrip: (
    mandiId: string,
    travelDate: string,
    totalCapacityQuintals: number,
    postedByPhone: string,
    postedByName?: string
  ) =>
    apiClient<{ status: string; trip: TruckTrip }>('/v1/farmer/truck-share/trips', {
      method: 'POST',
      body: JSON.stringify({
        mandi_id: mandiId,
        travel_date: travelDate,
        total_capacity_quintals: totalCapacityQuintals,
        posted_by_phone: postedByPhone,
        posted_by_name: postedByName,
      }),
    }),

  listTrips: (mandiId?: string, onOrAfter?: string) =>
    apiClient<{ trips: TruckTrip[] }>('/v1/farmer/truck-share/trips', {
      params: { ...(mandiId ? { mandi_id: mandiId } : {}), ...(onOrAfter ? { on_or_after: onOrAfter } : {}) },
    }),

  joinTrip: (tripId: string, quantityQuintals: number, joinerPhone: string, joinerName?: string) =>
    apiClient<{ status: string; trip: TruckTrip }>(`/v1/farmer/truck-share/trips/${tripId}/join`, {
      method: 'POST',
      body: JSON.stringify({
        quantity_quintals: quantityQuintals,
        joiner_phone: joinerPhone,
        joiner_name: joinerName,
      }),
    }),

  catalog: () => apiClient<FarmCatalog>('/v1/farmer/catalog'),

  overview: (district: string) => apiClient<FarmOverview>(`/v1/farmer/overview/${district}`),

  board: (district: string, crop: string) => apiClient<FarmBoard>(`/v1/farmer/board/${district}/${crop}`),

  sellPlan: (crop: string, mandiId: string, quantityQuintals: number) =>
    apiClient<SellPlanResult>(`/v1/farmer/sell-plan/${crop}/${mandiId}`, {
      params: { quantity_quintals: String(quantityQuintals) },
    }),

  mandi: (mandiId: string) => apiClient<MandiPage>(`/v1/farmer/mandi/${mandiId}`),

  accuracy: () => apiClient<AccuracyReport>('/v1/farmer/accuracy'),

  ask: (q: string, district?: string) =>
    apiClient<{ crop: CropId | null; district: string | null; understood: boolean }>('/v1/farmer/ask', {
      params: { q, ...(district ? { district } : {}) },
    }),

  nearestDistrict: (lat: number, lon: number) =>
    apiClient<{ district: string; distance_km: number }>('/v1/farmer/nearest-district', {
      params: { lat: String(lat), lon: String(lon) },
    }),

  priceOnDate: (commodity: string, mandiId: string, date: string) =>
    apiClient<PriceOnDateResult>(`/v1/farmer/price-on-date/${commodity}/${mandiId}`, {
      params: { date },
    }),

  listMandis: () => apiClient<{ mandis: MandiReference[] }>('/v1/farmer/mandis'),

  nearestMandis: (lat: number, lon: number, limit: number = 5) =>
    apiClient<{ mandis: NearestMandi[] }>('/v1/farmer/mandis/nearest', {
      params: { lat: String(lat), lon: String(lon), limit: String(limit) },
    }),
};
