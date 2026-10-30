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

export interface McPlace { mandi_id: string | null; name: string; name_kn: string; name_hi: string; hold_days: number; kind?: string }

export interface McBreakdownOption {
  option: McOption;
  parts: Array<{ key: 'price' | 'fee' | 'spoilage' | 'transport' | 'handling' | 'farm_gate_discount'; value: number }>;
  net: number;
}
export interface McBreakdown {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  as_of?: string;
  options?: Record<'recommended' | 'nearest_today' | 'highest_yesterday' | 'farm_gate', McBreakdownOption>;
  recommended_vs_nearest?: Record<string, number>;
  note?: string;
}

export interface McSweep {
  param: string;
  points: Array<{ x: number; mandi_id: string | null; name: string; hold_days: number; net: number }>;
  flips: Array<{ at: number; from: McPlace; to: McPlace }>;
}
export interface McSimulation {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  as_of?: string;
  scenario?: { transport_per_q_km: number; spoilage_per_day: number; market_fee: number; handling_per_trip: number; max_hold_days: number };
  defaults?: { transport_per_q_km: number; spoilage_per_day: number; market_fee: number; handling_per_trip: number };
  recommended?: McOption;
  default_recommended?: McOption;
  changed?: boolean;
  sweeps?: { transport: McSweep; spoilage: McSweep };
  note?: string;
}

export interface McCrowd {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  farmers?: number;
  quantity_per_farmer?: number;
  total_quintals?: number;
  price_flexibility?: number;
  flexibility_note?: string;
  recommended?: McPlace;
  recommended_yard_daily_arrivals_q?: number | null;
  alone?: { net_per_q: number };
  everyone_follows_best?: { net_per_q: number; price_drop_pct: number };
  everyone_goes_nearest?: { net_per_q: number };
  coordinated?: { net_per_q: number; split: Array<{ label: McPlace; share: number; quintals: number; net_per_q: number; price_drop_pct: number }> };
  gain_coordinated_vs_everyone_best_per_q?: number;
  gain_total_rs?: number;
}

export interface McReportingRow {
  mandi_id: string; name: string; name_kn: string; name_hi: string; district: string | null;
  reported_share: number; silent_share_open_days: number; closed_weekdays: string[]; silent_by_weekday: number[];
  worst_open_weekday: string; worst_open_weekday_silent: number; mean_price: number;
  expected_loss_per_q: number | null; expected_loss_pct: number | null;
}
export interface McReportingValue {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  window?: [string, string];
  silent_price_factor?: number;
  mandis?: McReportingRow[];
  mean_reported_share?: number;
  mean_expected_loss_per_q?: number;
  note?: string;
}

export interface McWtl { win: number; tie: number; loss: number; mean: number }
export interface McTrackWindow { days: number; vs_nearest: McWtl; vs_highest_yesterday: McWtl; floor_held_share: number }
export interface McTrackRecord {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop: string;
  window?: [string, string];
  days?: Array<{ date: string; recommended: number; nearest: number; highest_yesterday: number; oracle: number; floor: number; floor_held: number }>;
  last60?: McTrackWindow;
  all?: McTrackWindow;
  alpha?: number;
  note?: string;
  evidence_level?: 'strong' | 'limited';
}

export type McWhatIf = { transport?: number; spoilage?: number; fee?: number; handling?: number; maxHold?: number };

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

  breakdown: (crop: string, origin: McOrigin, quantityQuintals: number, alpha = 0.1, transportPerQKm?: number) =>
    apiClient<McBreakdown>(`/v1/market-choice/breakdown/${crop}`, {
      params: { ...originParams(origin), quantity_quintals: String(quantityQuintals), alpha: String(alpha), ...(transportPerQKm ? { transport_per_q_km: String(transportPerQKm) } : {}) },
    }),

  simulate: (crop: string, origin: McOrigin, quantityQuintals: number, w: McWhatIf, alpha = 0.1) =>
    apiClient<McSimulation>(`/v1/market-choice/simulate/${crop}`, {
      params: {
        ...originParams(origin),
        quantity_quintals: String(quantityQuintals),
        alpha: String(alpha),
        ...(w.transport !== undefined ? { transport_per_q_km: String(w.transport) } : {}),
        ...(w.spoilage !== undefined ? { spoilage_per_day: String(w.spoilage) } : {}),
        ...(w.fee !== undefined ? { market_fee: String(w.fee) } : {}),
        ...(w.handling !== undefined ? { handling_per_trip: String(w.handling) } : {}),
        ...(w.maxHold !== undefined ? { max_hold_days: String(w.maxHold) } : {}),
      },
    }),

  crowd: (crop: string, origin: McOrigin, farmers: number, quantityPerFarmer: number, priceFlexibility = 0.115, alpha = 0.1) =>
    apiClient<McCrowd>(`/v1/market-choice/crowd/${crop}`, {
      params: { ...originParams(origin), farmers: String(farmers), quantity_per_farmer: String(quantityPerFarmer), price_flexibility: String(priceFlexibility), alpha: String(alpha) },
    }),

  reportingValue: (crop: string) => apiClient<McReportingValue>(`/v1/market-choice/reporting-value/${crop}`),

  trackRecord: (crop: string) => apiClient<McTrackRecord>(`/v1/market-choice/track-record/${crop}`),
};
