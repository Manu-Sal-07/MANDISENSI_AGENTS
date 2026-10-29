/**
 * Supply-shock and cross-commodity API client (`api/shock_router.py`).
 *
 * The server decides what each audience may see: farmers only receive claims
 * whose evidence tier is ROBUST, traders also receive SUGGESTIVE ones with the
 * tier attached. A tier is never hidden or upgraded on the client.
 */

import { apiClient } from './api';
import type { McOption } from './marketChoiceApi';

export type Tier = 'ROBUST' | 'SUGGESTIVE' | 'NONE';
export type ShockState = 'glut' | 'squeeze' | 'normal';

export interface ShockArrivals {
  z: number;
  times_normal: number;
  as_of: string;
  age_days: number;
  state: ShockState;
  direction: 'glut' | 'squeeze' | null;
}

export interface ShockItem {
  crop: string;
  district: string;
  district_name: string;
  arrivals: ShockArrivals;
  price: { modal: number; change_7d_pct: number; as_of: string };
  response: { tier: Tier; typical_change_pct: number; horizon_days: number } | null;
  response_note: string;
  response_evidence: Record<string, unknown> | null;
  gap: {
    neighbours_dearer_by_pct: number;
    mean_gap_pct_last_8w: number;
    median_half_life_weeks: number | null;
    pairs_tested: number;
    pairs_closing: number;
    predicts_next_week: boolean;
    as_of: string;
  } | null;
  mandis: Array<{ mandi_id: string; mandi_name: string; z: number; as_of: string; state: ShockState; direction: 'glut' | 'squeeze' | null }>;
}

export interface CrossLink {
  source: string;
  target: string;
  shock: 'glut' | 'squeeze';
  tier: Tier;
  n_episodes: number;
  effect_pct: number | null;
  ci_pct: [number, number] | null;
  min_detectable_pct: number | null;
  placebo_p: number | null;
  armed_districts: string[];
  armed: boolean;
}

export interface ShockRadar {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  audience: 'farmer' | 'trader';
  as_of: string;
  items: ShockItem[];
  study: { available: boolean; generated_at?: string; farmer_tiers: string[]; own_crop: { n_tested: number; n_robust: number; n_suggestive: number } | null };
  cross_crop?: { status: string; n_tested?: number; n_robust?: number; n_suggestive?: number; links?: CrossLink[] };
}

export interface StudyRow {
  crop: string;
  direction: 'glut' | 'squeeze';
  horizon_days: number;
  n_episodes: number;
  tier: Tier;
  effect_pct: number;
  ci_pct: [number, number];
  typical_change_pct: number;
  share_price_fell: number;
  min_detectable_pct: number;
  placebo_p: number | null;
  holm_p: number | null;
}

export interface ShockStudy {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  generated_at?: string;
  data?: { from: string; to: string; crops: string[]; districts: string[] };
  rules?: { z_onset: number; horizons_days: number[]; min_episodes: number; placebo_draws: number; holm_over: number };
  n_tested?: number;
  n_robust?: number;
  n_suggestive?: number;
  results?: StudyRow[];
}

export interface Explanation {
  lang: 'en' | 'kn' | 'hi';
  headline: string;
  why: string[];
  cautions: string[];
  author: 'llm' | 'rules';
  model?: string;
  checks: {
    decision_unchanged?: boolean;
    sentences?: number;
    sentences_by_llm?: number;
    rejected?: Array<{ reason: string }>;
    llm_error?: string;
    latency_ms?: number;
  };
}

export interface ExplainResponse {
  status: 'OK' | 'UNAVAILABLE';
  reason?: string;
  crop?: string;
  recommended?: McOption;
  explanation?: Explanation;
  shock?: ShockItem | null;
}

export const shockApi = {
  radar: (audience: 'farmer' | 'trader', crop?: string, district?: string) =>
    apiClient<ShockRadar>('/v1/shock/radar', { params: { audience, ...(crop ? { crop } : {}), ...(district ? { district } : {}) } }),

  study: (audience: 'farmer' | 'trader' = 'trader') => apiClient<ShockStudy>('/v1/shock/study', { params: { audience } }),

  explain: (crop: string, origin: { district?: string; lat?: number; lon?: number }, quantity: number, alpha: number, rate: number, lang: string) =>
    apiClient<ExplainResponse>(`/v1/market-choice/explain/${crop}`, {
      params: {
        ...(origin.lat !== undefined && origin.lon !== undefined ? { lat: String(origin.lat), lon: String(origin.lon) } : {}),
        ...(origin.district ? { district: origin.district } : {}),
        quantity_quintals: String(quantity),
        alpha: String(alpha),
        transport_per_q_km: String(rate),
        lang,
      },
    }),
};
