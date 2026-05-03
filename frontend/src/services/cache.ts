/**
 * Layer 3: Service Infrastructure - Cache Prep
 * Purpose: Define structure for client-side caching.
 * ⚠️ DO NOT implement persistence logic in Phase 1.
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresIn: number;
}

const memoryCache = new Map<string, CacheEntry<any>>();

export const cacheService = {
  /**
   * Set a value in the cache
   */
  set: <T>(key: string, data: T, expiresInMs: number = 300000): void => {
    memoryCache.set(key, {
      data,
      timestamp: Date.now(),
      expiresIn: expiresInMs,
    });
  },

  /**
   * Get a value from the cache
   */
  get: <T>(key: string): T | null => {
    const entry = memoryCache.get(key);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > entry.expiresIn;
    if (isExpired) {
      memoryCache.delete(key);
      return null;
    }

    return entry.data as T;
  },

  /**
   * Clear the cache
   */
  clear: (): void => {
    memoryCache.clear();
  }
};
