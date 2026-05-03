import { MandiOpportunitySchema, MandiDetailSchema } from '@/types/schemas';
import { logger } from './logger';

/**
 * Phase 6: Production Hardening - API Layer
 * Transform "blind trust" into "validated resilience".
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

export const apiClient = async <T>(endpoint: string, options: RequestOptions = {}): Promise<T> => {
  const { params, ...customOptions } = options;
  const startTime = Date.now();
  
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
  }

  try {
    const response = await fetch(url.toString(), {
      ...customOptions,
      headers: {
        'Content-Type': 'application/json',
        ...customOptions.headers,
      },
    });

    const duration = Date.now() - startTime;
    logger.logDebug(`API Request: ${endpoint} took ${duration}ms`);

    if (!response.ok) {
      logger.logError(`API Failure: ${endpoint}`, { status: response.status, text: response.statusText });
      throw new Error(`API Request Error: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
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

  predictQuery: async (query: string): Promise<QueryResponse> => {
    const data = await apiClient<QueryResponse>('/query/', {
      method: 'POST',
      body: JSON.stringify({ query })
    });
    return data;
  }
};
