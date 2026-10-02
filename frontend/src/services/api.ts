import { MandiOpportunitySchema, MandiDetailSchema } from '@/types/schemas';
import { logger } from './logger';
import type { QueryResponse } from '@/types/mandi';

/**
 * Phase 6: Production Hardening - API Layer
 * Transform "blind trust" into "validated resilience".
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_LOCALHOST_FALLBACK = API_BASE_URL.includes('localhost')
  ? API_BASE_URL.replace('localhost', '127.0.0.1')
  : API_BASE_URL;

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

const makeApiRequest = async (url: string, customOptions: RequestInit) => {
  const headers: Record<string, string> = {
    ...((customOptions.headers ?? {}) as Record<string, string>),
  };

  if (customOptions.body && !Object.prototype.hasOwnProperty.call(headers, 'Content-Type')) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...customOptions,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API Request Error: ${response.statusText}`);
  }

  return response.json();
};

export const apiClient = async <T>(endpoint: string, options: RequestOptions = {}): Promise<T> => {
  const { params, ...customOptions } = options;
  const startTime = Date.now();
  const url = new URL(endpoint, API_BASE_URL);

  if (params) {
    Object.keys(params).forEach((key) => url.searchParams.append(key, params[key]));
  }

  try {
    const result = await makeApiRequest(url.toString(), customOptions);
    const duration = Date.now() - startTime;
    logger.logDebug(`API Request: ${endpoint} took ${duration}ms`);
    return result;
  } catch (error) {
    if (
      error instanceof TypeError &&
      error.message === 'Failed to fetch' &&
      API_LOCALHOST_FALLBACK !== API_BASE_URL
    ) {
      const fallbackUrl = new URL(endpoint, API_LOCALHOST_FALLBACK);
      if (params) {
        Object.keys(params).forEach((key) => fallbackUrl.searchParams.append(key, params[key]));
      }

      try {
        const fallbackResult = await makeApiRequest(fallbackUrl.toString(), customOptions);
        const duration = Date.now() - startTime;
        logger.logDebug(`API Request fallback: ${fallbackUrl.toString()} took ${duration}ms`);
        return fallbackResult;
      } catch (fallbackError) {
        logger.logError(`Network/API Exception fallback: ${endpoint}`, fallbackError);
        throw fallbackError;
      }
    }

    logger.logError(`Network/API Exception: ${endpoint}`, error);
    throw error;
  }
};

/**
 * Phase 2 - scheduled forecasting.
 *
 * The backend never trains or scores inside a request: a nightly job
 * publishes a forecast table and this reads it. Two consequences shape these
 * types.
 *
 * First, a point is not guaranteed. `status` carries a refusal reason
 * (INSUFFICIENT_HISTORY, DORMANT, REBUILDING_HISTORY, NO_PROMOTED_MODEL)
 * and every numeric field is null in that case, so the UI must render the
 * reason rather than a zero or a dash.
 *
 * Second, the interval is the decision-relevant output, not the point.
 * Measured skill over a naive "price unchanged" forecast is a few percent;
 * the empirical 90% band is what actually carries information, so anything
 * showing `forecastPrice` must show the band with it.
 */
export type ForecastStatus =
  | 'OK'
  | 'INSUFFICIENT_HISTORY'
  | 'DORMANT'
  | 'REBUILDING_HISTORY'
  // Emitted by forecasts published before segment-aware features landed;
  // kept so an older stored forecast still narrows to a known status.
  | 'DISCONTINUOUS_HISTORY'
  | 'NO_PROMOTED_MODEL';

export interface ForecastInterval {
  p05: number | null;
  p25: number | null;
  p75: number | null;
  p95: number | null;
}

export interface ForecastPoint {
  horizon_days: number | null;
  target_date: string | null;
  status: ForecastStatus;
  reason: string | null;
  forecast_price: number | null;
  expected_change_pct: number | null;
  direction: 'up' | 'down' | null;
  interval: ForecastInterval | null;
  /** 'row_conditional_quantile' when a dedicated quantile model has measurably
   * calibrated for this horizon (band width reflects this row's own
   * volatility/seasonal signals); 'pooled_residual' otherwise (a fold-fixed
   * offset from the point forecast). */
  interval_source: 'row_conditional_quantile' | 'pooled_residual' | null;
  /** 'xgboost_linear_blend' when a walk-forward measurement showed blending
   * with a regularised linear model beating the point model alone for this
   * horizon; 'xgboost' (point model only) otherwise. */
  prediction_source: 'xgboost_linear_blend' | 'xgboost' | null;
  /** SELL/HOLD/WAIT from the calibrated interval at a threshold whose
   * precision was measured on held-out folds for this horizon; WAIT for
   * every row at a horizon where no threshold cleared the bar. */
  decision: 'SELL' | 'HOLD' | 'WAIT' | null;
  decision_probability_of_decline: number | null;
  model_skill: number | null;
}

export interface ForecastCurve {
  commodity: string;
  mandi_id: string;
  as_of_date: string | null;
  last_observed_price: number | null;
  data_lag_days: number | null;
  history_rows: number | null;
  freshness: string | null;
  generated_at: string | null;
  points: ForecastPoint[];
  caveat?: string;
}

export interface ForecastServiceStatus {
  available: boolean;
  as_of_date: string | null;
  generated_at: string | null;
  model_version: string | null;
  series_count: number | null;
  forecast_rows: number | null;
  freshness: string | null;
  age_hours: number | null;
}

export const mandiApi = {
  getMandiFeed: async (mode: string = 'default', lat?: number, lon?: number) => {
    const data = await apiClient<any[]>('/api/mandi-feed', {
      params: { 
        mode,
        ...(lat !== undefined && { lat: lat.toString() }),
        ...(lon !== undefined && { lon: lon.toString() })
      }
    });

    // Part 3: Data Validation
    return (data || []).map(item => {
      const result = MandiOpportunitySchema.safeParse(item);
      if (!result.success) {
        logger.logWarn('Invalid MandiOpportunity received', result.error);
        return MandiOpportunitySchema.parse({}); // Fallback to safe defaults
      }
      return result.data;
    });
  },

  getMandiDetail: async (id: string) => {
    const data = await apiClient<any>(`/api/mandi/${id}`);
    
    // Part 3: Data Validation
    const result = MandiDetailSchema.safeParse(data);
    if (!result.success) {
      logger.logError(`Invalid MandiDetail for ${id}`, result.error);
      throw new Error('Mandi detail validation failed');
    }
    return result.data;
  },

  getDiscoveryFeed: async (location: string = 'bengaluru') => {
    return await apiClient<any[]>('/discovery/feed', {
      params: { location }
    });
  },

  getDiscoveryDetails: async (mandiId: string) => {
    return await apiClient<any>('/discovery/details', {
      params: { mandi_id: mandiId }
    });
  },

  getQuickDecisions: async (location: string = 'bengaluru') => {
    return await apiClient<any>('/discovery/quick-decisions', {
      params: { location }
    });
  },

  getCognitionAvailable: async () => {
    return await apiClient<Record<string, string[]>>('/v1/cognition/available');
  },

  getProcessedMarketDataOptions: async () => {
    return await apiClient<{ markets: Array<{ commodity: string; mandi_id: string }> }>('/v1/cognition/market-data/processed');
  },

  getCognitionDirectives: async () => {
    return await apiClient<{ directives: any[] }>('/v1/cognition/directives');
  },

  getMarketState: async (commodity: string, mandiId: string) => {
    return await apiClient<any>(`/v1/cognition/state/${commodity}/${mandiId}`);
  },

  getMarketTimeSeries: async (commodity: string, mandiId: string, limit: number = 365) => {
    return await apiClient<any>(`/v1/cognition/market-data/${commodity}/${mandiId}`, {
      params: { limit: limit.toString() },
    });
  },

  getMarketHistory: async (commodity: string, mandiId: string, limit: number = 50) => {
    return await apiClient<any>(`/v1/cognition/history/${commodity}/${mandiId}`, {
      params: { limit: limit.toString() },
    });
  },

  // Real daily price/volume history for any of the 5 commodities x 15
  // Karnataka APMC mandis, keyed by row rather than a filename guess — see
  // api/market_data_router.py. Used by Market Explorer instead of the
  // legacy market-data/history pair above, which silently mislabels or
  // 404s for most mandis outside the 2-mandi cognition registry.
  getTraderMarketHistory: async (commodity: string, mandiId: string) => {
    return await apiClient<{ commodity: string; mandi_id: string; history: Array<{ timestamp: string; price: number; arrivals: number }> }>(
      `/v1/market-data/history/${commodity}/${mandiId}`
    );
  },

  getTraderMarkets: async () => {
    return await apiClient<{ commodities: string[]; markets: Record<string, string[]> }>('/v1/market-data/markets');
  },

  getTraderComparison: async (mandiId: string, timeframe: 'week' | 'month' | 'year' = 'month') => {
    return await apiClient<{
      mandi_id: string;
      timeframe: string;
      series: Record<string, Array<{ time: string; value: number }>>;
      ranking: Array<{ commodity: string; change_pct: number }>;
    }>('/v1/market-data/compare', { params: { mandi_id: mandiId, timeframe } });
  },

  getCognitionStates: async () => {
    return await apiClient<any[]>('/v1/cognition/states');
  },

  getCognitionMemories: async () => {
    return await apiClient<any[]>('/v1/cognition/memories');
  },

  simulateMarketScenario: async (commodity: string, mandiId: string, scenario: string, params: Record<string, any> = {}) => {
    return await apiClient<any>('/v1/cognition/simulate', {
      method: 'POST',
      body: JSON.stringify({ commodity, mandi: mandiId, scenario_type: scenario, params }),
    });
  },

  predictQuery: async (query: string): Promise<QueryResponse> => {
    const data = await apiClient<QueryResponse>('/v1/query/', {
      method: 'POST',
      body: JSON.stringify({ query })
    });
    return data;
  },

  // ---- Phase 2: scheduled forecasting -------------------------------
  // The mandi ids used here are the same ones the Phase 1 cognition and
  // market-data surfaces use; the backend resolves them to canonical store
  // ids, so no id translation belongs on this side.

  /** Full horizon curve for a series. Omit `horizon` to get every published one. */
  getForecast: async (commodity: string, mandiId: string, horizon?: number) => {
    return await apiClient<ForecastCurve>(
      `/v1/forecast/${commodity}/${mandiId}`,
      horizon ? { params: { horizon: String(horizon) } } : {}
    );
  },

  /** Freshness, coverage and model version of the published store. Never fails. */
  getForecastStatus: async () => {
    return await apiClient<ForecastServiceStatus>('/v1/forecast/status');
  },

  // ---- LLM decision intelligence -------------------------------------
  // A structured brief reasoned over a fixed evidence bundle (cognition +
  // forecast + spillover), then verified so every stated figure traces back
  // to that bundle. `generated_by`/`model_id` say which provider actually
  // produced it — Claude when MANDISENSE_LLM_PROVIDER=claude and an API key
  // are configured on the backend, the deterministic rule-based composer
  // otherwise. Never fails: a misconfigured provider is reported, not thrown.

  getIntelligenceStatus: async () => {
    return await apiClient<IntelligenceStatus>('/v1/intelligence/status');
  },

  getIntelligenceBrief: async (commodity: string, mandiId: string, includeEvidence = false) => {
    return await apiClient<DecisionBrief>(
      `/v1/intelligence/brief/${commodity}/${mandiId}`,
      { params: includeEvidence ? { include_evidence: 'true' } : {} }
    );
  },

  getIntelligenceEvidence: async (commodity: string, mandiId: string) => {
    return await apiClient<Record<string, any>>(`/v1/intelligence/evidence/${commodity}/${mandiId}`);
  },
};

export interface IntelligenceStatus {
  available: boolean;
  provider: string;
  model_id: string | null;
  grounding_enforced: boolean;
  reason?: string;
}

export interface BriefFactor {
  label: string;
  detail: string;
  direction: 'supports' | 'opposes' | 'neutral';
  evidence_ref: string;
}

export interface DecisionBrief {
  commodity: string;
  mandi_id: string;
  action: string;
  confidence: string;
  headline: string;
  rationale: string;
  factors: BriefFactor[];
  risks: string[];
  watch_next: string[];
  generated_by: string;
  model_id: string | null;
  evidence_as_of: string | null;
  grounded: boolean;
  grounding_issues: string[];
  evidence: Record<string, any> | null;
  caveat: string;
}
