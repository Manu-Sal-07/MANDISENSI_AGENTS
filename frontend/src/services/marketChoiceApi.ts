/**
 * Market-choice API client: where and when to sell, with a verified revenue floor.
 *
 * One typed method per endpoint in `api/market_choice_router.py`. Same
 * convention as `farmerApi.ts`: every endpoint can answer
 * `status: "UNAVAILABLE"` with a reason instead of data (a crop without
 * enough mandis, or whose floor was never validated, is refused rather than
 * advised on), so callers must check `status` before reading any number.
 */

import { apiClient } from './api';

export type Alpha = 0.05 | 0.1 | 0.2;

export interface McOption {
  kind: 'mandi' | 'farm_gate';
  mandi_id: string | null;
  mandi_name: string;
  mandi_name_kn: string;
  mandi_name_hi: string;
  district: string | null;
  hold_days: number;
  sale_date: string;
  weekday: string;
  is_sunday: boolean;
  distance_km: number;
  expected_price: number;
  expected_net_per_q: number;
  floor_per_q: number;
  total_expected: number;
  total_floor: number;
  chance_open: number;
}

export interface McEvidence {
  status: 'OK' | 'INSUFFICIENT_HISTORY' | 'UNAVAILABLE';
  level?: 'strong' | 'limited';
  window?: [string, string];
  scored_days?: number;
  mean_net_revenue?: Record<string, number>;
  gain_vs_highest_yesterday?: { mean: number; ci_lo: number; ci_hi: number };
  gain_vs_nearest?: { mean: number; ci_lo: number; ci_hi: number };
  share_of_oracle_gap_closed?: number | null;
  silent_trip_rate?: number;
  floor_violation_adaptive?: Record<string, number>;
}

export interface McRecommendation {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  as_of?: string;
  decision_day?: string;
  origin?: { lat: number; lon: number; kind: string; label: string; label_kn?: string; label_hi?: string; nearest_district?: string };
  quantity_quintals?: number;
  alpha?: number;
  confidence_pct?: number;
  recommended?: McOption;
  safest?: McOption | null;
  alternatives?: McOption[];
  baselines?: { nearest_today: McOption | null; highest_yesterday: McOption | null; farm_gate: McOption | null };
  gain?: { vs_nearest_per_q: number | null; vs_highest_yesterday_per_q: number | null; vs_nearest_total: number | null };
  guarantee?: { alpha: number; multiplier: number; method: string; backtest_violation: number | null };
  assumptions?: {
    transport_per_q_km: number; road_factor: number; market_fee: number; handling_per_trip: number;
    spoilage_per_day: number; silent_price_factor: number; farmgate_factor: number;
    transport_presets: Record<string, number>;
  };
  evidence?: McEvidence;
  caveats?: string[];
  stale_mandis?: string[];
  model?: { trained_through: string; mandis: number; training_days: number };
}

export interface McMatrixRow {
  mandi_id: string;
  mandi_name: string;
  district: string;
  offered: boolean;
  distance_km: number;
  last_price: number;
  days_since_report: number;
  expected_price: number[];
  expected_net: number[];
  floor: number[];
  chance_open: number[];
}

export interface McMatrix {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  as_of?: string;
  decision_day?: string;
  alpha?: number;
  origin?: { lat: number; lon: number; label: string };
  mandis?: McMatrixRow[];
  farm_gate?: { expected_net: number; floor: number };
  best?: { mandi_id: string | null; hold_days: number };
  assumptions?: { transport_per_q_km: number; spoilage_per_day: number; market_fee: number; handling_per_trip: number };
  error_scale?: { multiplier: number };
}

export interface McCrops {
  crops: Array<{ crop: string; mandis: number; trained_through: string; limited_evidence: boolean; evidence: McEvidence }>;
  alphas: number[];
  default_alpha: number;
  origins: Array<{ id: string; name: string; name_kn: string; name_hi: string; lat: number; lon: number }>;
  transport_presets: Record<string, number>;
}

export interface McCalibration {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  trained_through?: string;
  alphas?: number[];
  multiplier_q?: Record<string, number> | null;
  calibration_scores?: number;
  backtest?: McEvidence & {
    monthly: { months: string[]; recommended: number[]; nearest: number[]; highest: number[]; oracle: number[] };
    floor_violation_static_out_of_sample: Record<string, number>;
    alpha_effective: Record<string, number>;
    safest_gain_vs_highest_yesterday: { mean: number; ci_lo: number; ci_hi: number };
  };
}

export interface ResearchEvidence {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  generated_at?: string;
  source?: string;
  study?: { crop: string; mandis: number; decision_days: number; folds: number; period: [string, string]; oracle_revenue: number; data: string };
  decision?: { methods: Array<{ method: string; label: string; class: 'realised' | 'observed' | 'heuristic'; revenue: number; regret: number; gap_closed: number; cvar10: number; fallback_rate: number }> };
  effects?: Array<{ label: string; diff: number; ci_lo: number; ci_hi: number; holm_p: number; verdict: 'better' | 'worse' | 'no_effect' }>;
  crops?: Array<{
    crop: string; markets: number; oracle: number; heuristic: number; observed_labels: number; realised_labels: number;
    label_effect: { diff: number; ci_lo: number; ci_hi: number; holm_p: number }; loss_effect: { diff: number; p: number };
  }>;
  floors?: Array<{ predictor: string; policy: string; alpha: number | null; violation: number; mean_floor: number; revenue: number; cvar10: number }>;
  leakage?: Array<{
    decomposer: string; forecaster: string; h: number; published: number; published_joint: number; causal_joint: number; raw: number;
    gap: number; gap_ci_lo: number; gap_ci_hi: number;
  }>;
  future_sensitivity?: Array<{ decomposer: string; median: number }>;
  foundation_model?: Record<string, number>;
  silence?: { reporting_delta_auc: number; returns_dm_p: number };
  forecast_vs_decision?: Array<{ method: string; label: string; skill_observed: number; skill_realised: number; gap_closed_vs_heuristic: number }>;
  negative_results?: Array<{ id: string; text: string }>;
  limitations?: string[];
  figures?: Array<{ id: string; title: string; caption: string; path: string }>;
}

export type McOrigin = { district?: string; mandiId?: string; lat?: number; lon?: number };

const originParams = (o: McOrigin): Record<string, string> => ({
  ...(o.lat !== undefined && o.lon !== undefined ? { lat: String(o.lat), lon: String(o.lon) } : {}),
  ...(o.mandiId ? { mandi_id: o.mandiId } : {}),
  ...(o.district ? { district: o.district } : {}),
});

export const marketChoiceApi = {
  crops: () => apiClient<McCrops>('/v1/market-choice/crops'),

  recommend: (crop: string, origin: McOrigin, quantityQuintals: number, alpha = 0.1, transportPerQKm?: number) =>
    apiClient<McRecommendation>(`/v1/market-choice/recommend/${crop}`, {
      params: {
        ...originParams(origin),
        quantity_quintals: String(quantityQuintals),
        alpha: String(alpha),
        ...(transportPerQKm ? { transport_per_q_km: String(transportPerQKm) } : {}),
      },
    }),

  matrix: (crop: string, origin: McOrigin, alpha = 0.1, transportPerQKm?: number) =>
    apiClient<McMatrix>(`/v1/market-choice/matrix/${crop}`, {
      params: { ...originParams(origin), alpha: String(alpha), ...(transportPerQKm ? { transport_per_q_km: String(transportPerQKm) } : {}) },
    }),

  calibration: (crop: string) => apiClient<McCalibration>(`/v1/market-choice/calibration/${crop}`),

  evidence: () => apiClient<ResearchEvidence>('/v1/market-choice/evidence'),
};
