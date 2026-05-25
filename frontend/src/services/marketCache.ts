import { mandiApi } from './api';

type Key = string; // `${commodity}|${mandiId}`

type MarketHistoryEntry = {
  timestamp: string;
  price_prediction: number;
  forecast_arrivals?: number;
  regime?: string;
  trend?: string;
  confidence?: { score?: number };
  volatility?: { score?: number; momentum?: number };
};

type MarketState = any;

type HistoricalSeriesEntry = {
  timestamp: string;
  date: string;
  price: number;
  arrivals: number;
  regime: string;
};

type ForecastOutput = {
  lastHistoricalPrice: number;
  currentPrice: number;
  delta: number;
  direction: 'up' | 'down' | 'flat';
};

type MarketAnalogPattern = {
  period: string;
  match: number;
  event: string;
  move: 'Up' | 'Down';
  direction: 'up' | 'down';
};

type DnaMetric = {
  axis: string;
  value: number;
  label: string;
};

type CorrelationMetrics = {
  arrivalPriceCorrelation: number;
  priceMomentumCorrelation: number | null;
};

type PriceMemoryEnvelope = {
  low: number;
  median: number;
  average: number;
  high: number;
  percentile: number;
  currentPosition: number;
};

type MarketAnalysis = {
  historicalSeries: HistoricalSeriesEntry[];
  arrivalHistory: { timestamp: string; arrivals: number }[];
  seasonalityIndex: number[];
  regimeTimeline: { timestamp: string; regime: string }[];
  forecastOutput: ForecastOutput | null;
  analogPatterns: MarketAnalogPattern[];
  dnaMetrics: DnaMetric[];
  correlation: CorrelationMetrics;
  priceMemory: PriceMemoryEnvelope | null;
  computedAt: string;
};

class MarketCache {
  private states = new Map<Key, MarketState>();
  private histories = new Map<Key, MarketHistoryEntry[]>();
  private analyses = new Map<Key, MarketAnalysis>();
  private allStates: MarketState[] = [];
  private initialized = false;

  isInitialized() {
    return this.initialized;
  }

  key(commodity: string, mandiId: string) {
    return `${commodity}|${mandiId}`;
  }

  getState(commodity: string, mandiId: string) {
    return this.states.get(this.key(commodity, mandiId)) ?? null;
  }

  getHistory(commodity: string, mandiId: string) {
    return this.histories.get(this.key(commodity, mandiId)) ?? [];
  }

  getAnalysis(commodity: string, mandiId: string) {
    return this.analyses.get(this.key(commodity, mandiId)) ?? null;
  }

  getAllStates() {
    return this.allStates;
  }

  getAvailableOptions() {
    return this.allStates.map((s: any) => ({ commodity: s.commodity, mandi_id: s.mandi_id }));
  }

  async init(preferMarket?: { commodity: string; mandi_id: string }) {
    if (this.initialized) return;
    try {
      const states = await mandiApi.getCognitionStates();
      this.allStates = Array.isArray(states) ? states : [];
      this.allStates.forEach((s: any) => {
        const k = this.key(s.commodity, s.mandi_id);
        this.states.set(k, s);
      });

      if (preferMarket) {
        const { commodity, mandi_id } = preferMarket;
        await this.loadMarketAnalysis(commodity, mandi_id);
      }

      const uniqueCommodities = Array.from(new Set(this.allStates.map((s: any) => s.commodity)));
      const sample = uniqueCommodities.slice(0, 4);
      const marketsToPrefetch: Array<{ commodity: string; mandi: string }> = [];
      sample.forEach((commodity) => {
        const sampleState = this.allStates.find((st: any) => st.commodity === commodity);
        if (sampleState) marketsToPrefetch.push({ commodity, mandi: sampleState.mandi_id });
      });

      marketsToPrefetch.forEach((market) => {
        this.loadMarketAnalysis(market.commodity, market.mandi).catch((e) => {
          console.warn('MarketCache.init prefetch failed', market.commodity, market.mandi, e);
        });
      });
      this.initialized = true;
    } catch (e) {
      console.error('MarketCache.init error', e);
      this.initialized = true;
    }
  }

  async loadMarketHistory(commodity: string, mandiId: string, limit: number = 120) {
    const k = this.key(commodity, mandiId);
    if (this.histories.has(k)) return this.histories.get(k);
    try {
      const res = await mandiApi.getMarketHistory(commodity, mandiId, limit);
      const history = Array.isArray(res?.history) ? res.history : [];
      this.histories.set(k, history);
      return history;
    } catch (e) {
      console.error('loadMarketHistory failed', commodity, mandiId, e);
      this.histories.set(k, []);
      return [];
    }
  }

  async loadMarketAnalysis(commodity: string, mandiId: string, limit: number = 120) {
    const k = this.key(commodity, mandiId);
    if (this.analyses.has(k)) return this.analyses.get(k);
    try {
      await this.ensureMarketLoaded(commodity, mandiId);
      const history = this.getHistory(commodity, mandiId) ?? [];
      const state = this.getState(commodity, mandiId);
      const safeHistory = Array.isArray(history)
        ? history.filter((entry) => entry && typeof entry.timestamp === 'string' && entry.timestamp.trim().length > 0)
        : [];

      const seasonalityIndex = this.computeSeasonalityIndex(safeHistory);
      const analysis: MarketAnalysis = {
        historicalSeries: this.computeHistoricalSeries(safeHistory),
        arrivalHistory: safeHistory.map((entry) => ({ timestamp: entry.timestamp, arrivals: entry.forecast_arrivals ?? 0 })),
        seasonalityIndex,
        regimeTimeline: this.computeRegimeTimeline(safeHistory),
        forecastOutput: this.computeForecastOutput(state, safeHistory),
        analogPatterns: this.computeAnalogPatterns(state),
        dnaMetrics: this.computeDnaMetrics(state, seasonalityIndex),
        correlation: this.computeCorrelationMetrics(safeHistory, state),
        priceMemory: this.computePriceMemory(safeHistory, state),
        computedAt: new Date().toISOString(),
      };
      this.analyses.set(k, analysis);
      return analysis;
    } catch (e) {
      console.error('MarketCache.loadMarketAnalysis failed', commodity, mandiId, e);
      const fallback = this.buildFallbackAnalysis(this.getState(commodity, mandiId), this.getHistory(commodity, mandiId) ?? []);
      this.analyses.set(k, fallback);
      return fallback;
    }
  }

  async prefetchAdjacent(selected: { commodity: string; mandi_id: string }) {
    const others = this.allStates.filter((s: any) => !(s.commodity === selected.commodity && s.mandi_id === selected.mandi_id));
    const pick = others.slice(0, 4);
    pick.forEach((s: any) => {
      this.loadMarketAnalysis(s.commodity, s.mandi_id).catch((e) => {
        console.warn('MarketCache.prefetchAdjacent failed', s.commodity, s.mandi_id, e);
      });
    });
  }

  async ensureMarketLoaded(commodity: string, mandiId: string) {
    const k = this.key(commodity, mandiId);
    if (!this.states.has(k)) {
      try {
        const s = await mandiApi.getMarketState(commodity, mandiId);
        this.states.set(k, s);
      } catch (e) {
        console.error('ensureMarketLoaded: state failed', commodity, mandiId, e);
      }
    }
    if (!this.histories.has(k)) {
      await this.loadMarketHistory(commodity, mandiId);
    }
  }

  private computeHistoricalSeries(history: MarketHistoryEntry[]) {
    const sorted = history
      .slice()
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    return sorted.map((entry) => ({
      timestamp: entry.timestamp,
      date: new Date(entry.timestamp).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }),
      price: entry.price_prediction,
      arrivals: entry.forecast_arrivals ?? 0,
      regime: entry.regime || entry.trend || 'Unknown',
    }));
  }

  private computeSeasonalityIndex(history: MarketHistoryEntry[]) {
    const monthly = Array.from({ length: 12 }, () => ({ sum: 0, count: 0 }));
    history.forEach((entry) => {
      const month = new Date(entry.timestamp).getMonth();
      if (!Number.isInteger(month) || month < 0 || month > 11) return;
      const bucket = monthly[month];
      if (!bucket) return;
      bucket.sum += Number(entry.price_prediction ?? 0);
      bucket.count += 1;
    });
    const values = monthly.map((bucket) => (bucket.count ? bucket.sum / bucket.count : 0));
    const max = Math.max(...values, 1);
    return values.map((value) => Math.round((value / max) * 110));
  }

  private buildFallbackAnalysis(state: MarketState | null, history: MarketHistoryEntry[] = []): MarketAnalysis {
    const safeHistory = Array.isArray(history)
      ? history.filter((entry) => entry && typeof entry.timestamp === 'string' && entry.timestamp.trim().length > 0)
      : [];
    const seasonalityIndex = this.computeSeasonalityIndex(safeHistory);
    return {
      historicalSeries: this.computeHistoricalSeries(safeHistory),
      arrivalHistory: safeHistory.map((entry) => ({ timestamp: entry.timestamp, arrivals: entry.forecast_arrivals ?? 0 })),
      seasonalityIndex,
      regimeTimeline: this.computeRegimeTimeline(safeHistory),
      forecastOutput: this.computeForecastOutput(state, safeHistory),
      analogPatterns: this.computeAnalogPatterns(state),
      dnaMetrics: this.computeDnaMetrics(state, seasonalityIndex),
      correlation: this.computeCorrelationMetrics(safeHistory, state),
      priceMemory: this.computePriceMemory(safeHistory, state),
      computedAt: new Date().toISOString(),
    };
  }

  private computeRegimeTimeline(history: MarketHistoryEntry[]) {
    const sorted = history
      .slice()
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    const timeline: { timestamp: string; regime: string }[] = [];
    sorted.forEach((entry) => {
      const regime = entry.regime || entry.trend || 'Unknown';
      if (!timeline.length || timeline[timeline.length - 1].regime !== regime) {
        timeline.push({ timestamp: entry.timestamp, regime });
      }
    });
    return timeline.slice(-10);
  }

  private computeForecastOutput(state: MarketState | null, history: MarketHistoryEntry[]) {
    if (!state || !history.length) return null;
    const sorted = history
      .slice()
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    const lastPrice = sorted[sorted.length - 1]?.price_prediction ?? Number(state.price_prediction ?? 0);
    const currentPrice = Number(state.price_prediction ?? 0);
    const delta = currentPrice - lastPrice;
    const direction: ForecastOutput['direction'] = Math.abs(delta) < 0.5 ? 'flat' : delta > 0 ? 'up' : 'down';
    return {
      lastHistoricalPrice: lastPrice,
      currentPrice,
      delta,
      direction,
    } as ForecastOutput;
  }

  private computeAnalogPatterns(state: MarketState | null) {
    const analogs = state?.historical_analogs ?? [];
    if (!Array.isArray(analogs) || !analogs.length) return [];
    return analogs.slice(0, 4).map((analog: any): MarketAnalogPattern => {
      const isDown = String(analog.directive || '').toLowerCase().includes('down');
      return {
        period: analog.timestamp ? new Date(analog.timestamp).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : 'Unknown',
        match: Math.round((analog.similarity ?? 0) * 100),
        event: analog.directive || analog.regime || 'Historical analog',
        move: isDown ? 'Down' : 'Up',
        direction: isDown ? 'down' : 'up',
      };
    });
  }

  private computeDnaMetrics(state: MarketState | null, seasonalityIndex: number[]) {
    const volatilityScore = Math.round(Math.min(100, Math.max(0, (state?.volatility?.score ?? 0.5) * 100)));
    const confidenceScore = Math.round(Math.min(100, Math.max(0, (state?.confidence?.score ?? 0.5) * 100)));
    const freshnessScore = Math.round(Math.min(100, Math.max(0, (state?.freshness?.integrity_score ?? 0.75) * 100)));
    const momentumValue = Math.round(Math.min(100, Math.max(0, (state?.volatility?.momentum ?? 0) * 100)));
    const trendValue = state?.trend?.toLowerCase() === 'upward' ? 80 : state?.trend?.toLowerCase() === 'downward' ? 40 : 60;
    const seasonalityValue = seasonalityIndex.length ? Math.round(seasonalityIndex.reduce((sum, v) => sum + v, 0) / seasonalityIndex.length) : 65;
    return [
      { axis: 'Volatility', value: volatilityScore, label: 'Live volatility signal' },
      { axis: 'Forecast Stability', value: confidenceScore, label: 'Confidence in the latest market view' },
      { axis: 'Freshness', value: freshnessScore, label: 'Integrity of current intelligence' },
      { axis: 'Momentum', value: momentumValue, label: 'Regime momentum from recent history' },
      { axis: 'Trend Bias', value: trendValue, label: 'Direction of the latest forecast' },
      { axis: 'Seasonality', value: seasonalityValue, label: 'Aggregate seasonal pressure' },
    ];
  }

  private computeCorrelationMetrics(history: MarketHistoryEntry[], state: MarketState | null) {
    const values = history.filter((entry) => entry.forecast_arrivals !== undefined).map((entry) => ({ price: entry.price_prediction, arrivals: entry.forecast_arrivals ?? 0 }));
    if (values.length < 2) {
      return { arrivalPriceCorrelation: 0, priceMomentumCorrelation: state?.volatility?.momentum ?? null };
    }
    const priceMean = values.reduce((sum, v) => sum + v.price, 0) / values.length;
    const arrivalsMean = values.reduce((sum, v) => sum + v.arrivals, 0) / values.length;
    const covariance = values.reduce((sum, v) => sum + (v.price - priceMean) * (v.arrivals - arrivalsMean), 0) / values.length;
    const priceStd = Math.sqrt(values.reduce((sum, v) => sum + Math.pow(v.price - priceMean, 2), 0) / values.length);
    const arrivalsStd = Math.sqrt(values.reduce((sum, v) => sum + Math.pow(v.arrivals - arrivalsMean, 2), 0) / values.length);
    const correlation = priceStd && arrivalsStd ? covariance / (priceStd * arrivalsStd) : 0;
    return {
      arrivalPriceCorrelation: Number(correlation.toFixed(2)),
      priceMomentumCorrelation: state?.volatility?.momentum ?? null,
    };
  }

  private computePriceMemory(history: MarketHistoryEntry[], state: MarketState | null) {
    if (!history.length) return null;
    const prices = history.map((entry) => entry.price_prediction).sort((a, b) => a - b);
    const sum = prices.reduce((acc, price) => acc + price, 0);
    const average = sum / prices.length;
    const median = prices.length % 2 === 0 ? (prices[prices.length / 2 - 1] + prices[prices.length / 2]) / 2 : prices[(prices.length - 1) / 2];
    const current = state?.price_prediction ?? prices[prices.length - 1];
    const percentile = prices.length ? Math.round((prices.filter((value) => value <= current).length / prices.length) * 100) : 0;
    return {
      low: prices[0],
      median,
      average,
      high: prices[prices.length - 1],
      percentile,
      currentPosition: current,
    };
  }
}

const marketCache = new MarketCache();
export type { MarketAnalysis, HistoricalSeriesEntry };
export default marketCache;
