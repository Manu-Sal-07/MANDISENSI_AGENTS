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
  }
};
