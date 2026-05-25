'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState, useRef } from 'react';
import { apiClient, mandiApi } from '@/services/api';
import marketCache, { MarketAnalysis, HistoricalSeriesEntry } from '@/services/marketCache';
import {
  TrendingUp,
  Sliders,
  Calendar,
  Share2,
  Maximize2,
  CalendarDays,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Layers,
  Info,
  ChevronRight,
  TrendingDown,
  Percent,
  Search,
  BookOpen,
  ArrowRightLeft,
  ChevronDown
} from 'lucide-react';

type MarketOption = {
  commodity: string;
  mandi_id: string;
};

type MarketHistoryEntry = {
  timestamp: string;
  price_prediction: number;
  forecast_arrivals?: number;
  regime?: string;
  trend?: string;
  confidence?: { score?: number };
  volatility?: { score?: number; momentum?: number };
};

type MarketState = {
  commodity: string;
  mandi_id: string;
  timestamp: string;
  price_prediction: number;
  confidence?: {
    score?: number;
    stability?: number;
    last_updated?: string;
  };
  volatility?: {
    regime?: string;
    score?: number;
    is_escalating?: boolean;
    momentum?: number;
  };
  regime?: string;
  risk_level?: string;
  integrity_status?: string;
  forecast_arrivals?: number;
  trend?: string;
  deliberation?: {
    agents?: Array<{ agent_id?: string; signal?: string; confidence?: number; weight?: number }>;
    contradictions?: string[];
    dominant_agent_id?: string;
    chaos_score?: number;
  };
  freshness?: {
    last_computed?: string;
    integrity_score?: number;
    expiration_threshold_minutes?: number;
  };
  metadata?: Record<string, any>;
  directives?: Array<{ primary_directive?: string; urgency?: string }>; 
  historical_analogs?: Array<{ timestamp: string; similarity: number; regime?: string; directive?: string }>;
};

// Canonical list of all research markets to ensure dropdown always has complete coverage
const ALL_MARKETS: MarketOption[] = [
  { commodity: 'tomato', mandi_id: 'kolar_apmc' },
  { commodity: 'tomato', mandi_id: 'bangalore_yeshwanthpur' },
  { commodity: 'onion', mandi_id: 'lasalgaon_apmc' },
  { commodity: 'onion', mandi_id: 'hoskote_apmc' },
  { commodity: 'potato', mandi_id: 'agra_apmc' },
  { commodity: 'potato', mandi_id: 'anekal_apmc' },
  { commodity: 'garlic', mandi_id: 'neemuch_apmc' },
  { commodity: 'garlic', mandi_id: 'sidlaghatta_apmc' },
  { commodity: 'ginger', mandi_id: 'bangalore_apmc' },
  { commodity: 'ginger', mandi_id: 'channapatna_apmc' },
  { commodity: 'dry_chillis', mandi_id: 'guntur_apmc' }
];

const formatPrice = (price: number | null | undefined) => {
  if (price === null || price === undefined || Number.isNaN(price)) return '--';
  return new Intl.NumberFormat('en-IN').format(Math.round(price));
};

const formatLabel = (market: MarketOption) =>
  `${market.commodity.toUpperCase()} • ${market.mandi_id.replace('_apmc', '').toUpperCase()}`;

export default function MarketExplorerPage() {
  const [marketOptions, setMarketOptions] = useState<MarketOption[]>(ALL_MARKETS);
  const [selectedMarket, setSelectedMarket] = useState<MarketOption | null>(ALL_MARKETS[0]);
  const [marketState, setMarketState] = useState<MarketState | null>(null);
  const [marketHistory, setMarketHistory] = useState<MarketHistoryEntry[]>([]);
  const [marketAnalysis, setMarketAnalysis] = useState<MarketAnalysis | null>(null);
  const [displaySeries, setDisplaySeries] = useState<HistoricalSeriesEntry[]>([]);
  const [allStates, setAllStates] = useState<MarketState[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Custom interactive states for Stripe/Linear look
  const [timeRange, setTimeRange] = useState<'1Y' | '3Y' | '5Y' | '10Y' | 'ALL'>('3Y');
  const [hoveredPoint, setHoveredPoint] = useState<any | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [activeTab, setActiveTab] = useState<'dna' | 'narrative' | 'comparison'>('dna');
  
  // Replay Engine States
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [replaySpeed, setReplaySpeed] = useState<1 | 2 | 3>(1);
  const replayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Comparison Lab States
  const [compareList, setCompareList] = useState<string[]>(['tomato', 'onion', 'potato']);

  const getSeriesForRange = (series: HistoricalSeriesEntry[], range: typeof timeRange) => {
    if (!series.length) return [];
    const length = range === '1Y' ? 12 : range === '3Y' ? 24 : range === '5Y' ? 36 : series.length;
    return series.slice(-length);
  };
  
  useEffect(() => {
    // Initialize market cache and preload default market history
    let mounted = true;
    const init = async () => {
      setIsInitialLoading(true);
      try {
        await marketCache.init(selectedMarket || ALL_MARKETS[0]);
        if (!mounted) return;
        const opts = marketCache.getAvailableOptions();
        setMarketOptions(opts.length ? opts : ALL_MARKETS);
        setSelectedMarket((prev) => prev || opts[0] || ALL_MARKETS[0]);
      } catch (e) {
        setMarketOptions(ALL_MARKETS);
        setSelectedMarket((prev) => prev || ALL_MARKETS[0]);
      } finally {
        setIsInitialLoading(false);
      }
    };
    init();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedMarket) return;

    const cachedState = marketCache.getState(selectedMarket.commodity, selectedMarket.mandi_id);
    const cachedHistory = marketCache.getHistory(selectedMarket.commodity, selectedMarket.mandi_id);
    const cachedAnalysis = marketCache.getAnalysis(selectedMarket.commodity, selectedMarket.mandi_id);
    setMarketState(cachedState);
    setMarketHistory(cachedHistory || []);
    setMarketAnalysis(cachedAnalysis);
    setDisplaySeries(getSeriesForRange(cachedAnalysis?.historicalSeries ?? [], timeRange));
    setAllStates(marketCache.getAllStates());

    marketCache.loadMarketAnalysis(selectedMarket.commodity, selectedMarket.mandi_id)
      .then((analysis) => {
        if (analysis) {
          setMarketState(marketCache.getState(selectedMarket.commodity, selectedMarket.mandi_id));
          setMarketHistory(marketCache.getHistory(selectedMarket.commodity, selectedMarket.mandi_id));
          setMarketAnalysis(analysis);
          setDisplaySeries(getSeriesForRange(analysis.historicalSeries, timeRange));
        }
      })
      .catch((error) => {
        console.error('MarketCache.loadMarketAnalysis failed', error);
        setError('Unable to refresh market intelligence; showing cached values.');
      });

    marketCache.prefetchAdjacent(selectedMarket);
  }, [selectedMarket, timeRange]);

  const historicalSeries = displaySeries;
  const seasonalityIndex = marketAnalysis?.seasonalityIndex ?? Array(12).fill(100);
  const dnaMetrics = marketAnalysis?.dnaMetrics ?? [
    { axis: 'Volatility', value: 50, label: 'Live volatility signal' },
    { axis: 'Forecast Stability', value: 50, label: 'Confidence in the latest market view' },
    { axis: 'Freshness', value: 75, label: 'Integrity of current intelligence' },
    { axis: 'Momentum', value: 50, label: 'Regime momentum from recent history' },
    { axis: 'Trend Bias', value: 60, label: 'Direction of the latest forecast' },
    { axis: 'Seasonality', value: 80, label: 'Aggregate seasonal pressure' },
  ];
  const radarPoints = useMemo(() => {
    const center = 90;
    const r = 70;
    return dnaMetrics.map((metric, index) => {
      const angle = (index * 2 * Math.PI) / dnaMetrics.length - Math.PI / 2;
      const rawValue = typeof metric.value === 'number' && !Number.isNaN(metric.value) ? metric.value : 0;
      const val = Math.max(0, Math.min(1, rawValue / 100));
      return {
        x: center + r * val * Math.cos(angle),
        y: center + r * val * Math.sin(angle),
        label: metric.axis,
      };
    });
  }, [dnaMetrics]);
  const similarPatterns = marketAnalysis?.analogPatterns ?? [];
  const forecastOutput = marketAnalysis?.forecastOutput;

  useEffect(() => {
    if (isReplaying) {
      replayTimerRef.current = setInterval(() => {
        setReplayIndex((prev) => {
          if (prev >= historicalSeries.length - 1) {
            return 0;
          }
          return prev + 1;
        });
      }, 1000 / replaySpeed);
    } else {
      if (replayTimerRef.current) {
        clearInterval(replayTimerRef.current);
      }
    }
    return () => {
      if (replayTimerRef.current) clearInterval(replayTimerRef.current);
    };
  }, [isReplaying, historicalSeries, replaySpeed]);

  const currentReplayPoint = historicalSeries[replayIndex] || historicalSeries[0];

  // SVG Calculations for interactive charts
  const chartHeight = 360;
  const chartWidth = 920;
  const prices = historicalSeries.length ? historicalSeries.map((d) => d.price) : [0, 1];
  const minPrice = Math.min(...prices) * 0.95;
  const maxPrice = Math.max(...prices) * 1.08;
  const priceRange = Math.max(1, maxPrice - minPrice);

  const svgPoints = useMemo(() => {
    if (historicalSeries.length === 0) return [];
    return historicalSeries.map((d, index) => {
      const x = (index / (historicalSeries.length - 1)) * (chartWidth - 80) + 40;
      const y = chartHeight - ((d.price - minPrice) / priceRange) * (chartHeight - 80) - 40;
      return { x, y, data: d };
    });
  }, [historicalSeries, minPrice, priceRange]);

  const pathD = useMemo(() => {
    if (svgPoints.length === 0) return '';
    return svgPoints.reduce((acc, p, i, arr) => {
      if (i === 0) return `M ${p.x} ${p.y}`;
      const prev = arr[i - 1];
      const cp1x = prev.x + (p.x - prev.x) / 3;
      const cp1y = prev.y;
      const cp2x = prev.x + 2 * (p.x - prev.x) / 3;
      const cp2y = p.y;
      return `${acc} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p.x} ${p.y}`;
    }, '');
  }, [svgPoints]);

  const forecastPoints = forecastOutput && svgPoints.length > 0 ? [
    {
      x: svgPoints[svgPoints.length - 1].x + 40,
      y: chartHeight - ((forecastOutput.currentPrice - minPrice) / priceRange) * (chartHeight - 80) - 40,
      price: forecastOutput.currentPrice,
    }
  ] : [];

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 transition-colors duration-200">
      {/* Upper sub-header bar */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded-lg">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Market Explorer</h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Advanced Commodity Intelligence & Research Terminal</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedMarket ? `${selectedMarket.commodity}|${selectedMarket.mandi_id}` : ''}
              onChange={(e) => {
                const [commodity, mandi_id] = e.target.value.split('|');
                const next = marketOptions.find((o) => o.commodity === commodity && o.mandi_id === mandi_id);
                if (next) setSelectedMarket(next);
              }}
              className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-3 py-2 text-xs font-semibold shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              {marketOptions.map((market) => (
                <option key={`${market.commodity}-${market.mandi_id}`} value={`${market.commodity}|${market.mandi_id}`}>
                  {formatLabel(market)}
                </option>
              ))}
            </select>

            <div className="flex items-center rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-900 p-0.5 shadow-sm">
              {(['1Y', '3Y', '5Y', 'ALL'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range === 'ALL' ? 'ALL' : range)}
                  className={`rounded-md px-2.5 py-1 text-[11px] font-bold uppercase transition-all ${
                    timeRange === range
                      ? 'bg-white dark:bg-zinc-850 text-zinc-900 dark:text-white shadow-sm'
                      : 'text-zinc-505 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN - Research Summary, DNA Profile, Comparison Lab */}
        <div className="lg:col-span-4 space-y-8">
          
          {/* Section 1: Market Research Header / Overview info */}
          <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
            <div className="space-y-1">
              <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Current Market Position</span>
              <h2 className="text-2xl font-extrabold tracking-tight">
                {selectedMarket?.commodity.toUpperCase()}
              </h2>
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">{selectedMarket?.mandi_id.replace('_apmc', '').toUpperCase()} APMC Depot</p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 pt-6 border-t border-zinc-100 dark:border-zinc-800">
              <div>
                <span className="text-[9px] font-bold uppercase text-zinc-400 tracking-wider">Benchmark price</span>
                <p className="text-lg font-extrabold mt-0.5">
                  ₹{formatPrice(marketState?.price_prediction)}
                  <span className="text-[10px] text-zinc-400 font-medium ml-1">/ Quintal</span>
                </p>
              </div>
              <div>
                <span className="text-[9px] font-bold uppercase text-zinc-400 tracking-wider">Active regime</span>
                <span className="inline-flex items-center gap-1 text-[11px] font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  {marketState?.regime || 'Stable'}
                </span>
              </div>
            </div>
          </div>

          {/* TAB SELECTOR FOR DETAILS */}
          <div className="flex border-b border-zinc-200 dark:border-zinc-800">
            {(['dna', 'narrative', 'comparison'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === tab
                    ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400 font-extrabold'
                    : 'border-transparent text-zinc-400 hover:text-zinc-650 hover:text-zinc-600'
                }`}
              >
                {tab === 'dna' ? 'Market DNA' : tab === 'narrative' ? 'Market Story' : 'Comparison Lab'}
              </button>
            ))}
          </div>

          {/* Section 7: MARKET DNA Radar profile */}
          {activeTab === 'dna' && (
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-zinc-400 mb-4 flex items-center justify-between">
                <span>Commodity DNA Profile</span>
                <Info className="w-3.5 h-3.5" />
              </h3>

              <div className="flex justify-center my-4">
                <svg width="180" height="180" viewBox="0 0 180 180" className="overflow-visible">
                  {/* Grid rings */}
                  {[0.25, 0.5, 0.75, 1.0].map((scale, i) => (
                    <circle
                      key={i}
                      cx="90"
                      cy="90"
                      r={70 * scale}
                      fill="none"
                      stroke="rgba(148, 163, 184, 0.15)"
                      strokeWidth="1"
                    />
                  ))}
                  {/* Axes lines */}
                  {Array.from({ length: 6 }).map((_, i) => {
                    const angle = (i * 2 * Math.PI) / 6 - Math.PI / 2;
                    return (
                      <line
                        key={i}
                        x1="90"
                        y1="90"
                        x2={90 + 70 * Math.cos(angle)}
                        y2={90 + 70 * Math.sin(angle)}
                        stroke="rgba(148, 163, 184, 0.12)"
                        strokeWidth="1"
                      />
                    );
                  })}
                  {/* Radar shape */}
                  <polygon
                    points={radarPoints.map((p) => `${p.x},${p.y}`).join(' ')}
                    fill="rgba(16, 185, 129, 0.08)"
                    stroke="rgba(16, 185, 129, 0.6)"
                    strokeWidth="2"
                  />
                  {/* Radar vertices dots */}
                  {radarPoints.map((p, i) => (
                    <circle key={i} cx={p.x} cy={p.y} r="3" fill="rgb(16, 185, 129)" />
                  ))}
                </svg>
              </div>

              <div className="space-y-3 mt-6">
                {dnaMetrics.map((metric, i) => (
                  <div key={i} className="flex justify-between items-center text-xs">
                    <span className="text-zinc-505 dark:text-zinc-400 font-medium">{metric.axis}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500" style={{ width: `${metric.value}%` }} />
                      </div>
                      <span className="font-extrabold w-6 text-right">{metric.value}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 11: MARKET STORY research narrative */}
          {activeTab === 'narrative' && (
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-emerald-500" />
                <h3 className="text-xs font-black uppercase tracking-[0.2em] text-zinc-400">Research Digest</h3>
              </div>
              
              <div className="text-xs leading-relaxed space-y-3 text-zinc-600 dark:text-zinc-300">
                <p>
                  Live intelligence for <span className="font-extrabold text-zinc-950 dark:text-white">{selectedMarket?.commodity.toUpperCase()}</span> at {selectedMarket?.mandi_id.replace('_apmc', '').toUpperCase()} is sourced from the latest evolved market state and recent historical snapshots.
                </p>
                <p>
                  Current forecast direction is <span className="font-bold text-emerald-600 dark:text-emerald-300">{marketState?.trend ?? 'unknown'}</span>, with confidence {marketState?.confidence?.score?.toFixed(2) ?? '—'} and a current integrity score of {marketState?.freshness?.integrity_score ?? '—'}.
                </p>
                <p className="bg-zinc-50 dark:bg-zinc-950 p-3 rounded-lg border border-zinc-150 dark:border-zinc-800 italic">
                  {marketState?.directives?.[0]?.primary_directive ?? 'No directive narrative available for this market snapshot.'}
                </p>
              </div>
            </div>
          )}

          {/* Section 10: COMPARISON LAB */}
          {activeTab === 'comparison' && (
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-zinc-400 flex items-center justify-between">
                <span>Commodity Performance Matrix</span>
                <ArrowRightLeft className="w-3.5 h-3.5" />
              </h3>

              <div className="space-y-3">
                {compareList.map((commodityKey) => {
                  const state = allStates.find((s) => s.commodity === commodityKey);
                  const volatility = state?.volatility?.score ?? null;
                  return (
                    <button
                      key={commodityKey}
                      onClick={() => {
                        setCompareList((prev) =>
                          prev.includes(commodityKey) ? prev.filter((item) => item !== commodityKey) : [...prev, commodityKey]
                        );
                      }}
                      className={`w-full flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                        allStates.some((s) => s.commodity === commodityKey)
                          ? 'border-emerald-500 bg-emerald-50/20 dark:bg-emerald-950/10'
                          : 'border-zinc-150 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-850'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${
                          commodityKey === 'tomato' ? 'bg-red-500' : commodityKey === 'onion' ? 'bg-amber-500' : commodityKey === 'potato' ? 'bg-yellow-600' : 'bg-emerald-600'
                        }`} />
                        <span className="text-xs font-bold uppercase">{commodityKey}</span>
                      </div>
                      <div className="text-right text-[11px]">
                        <span className="text-zinc-400">Live volatility: </span>
                        <span className="font-extrabold">{volatility !== null ? volatility.toFixed(2) : 'N/A'}</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Lab interactive micro chart mapping comparative lines */}
              <div className="pt-4 border-t border-zinc-150 dark:border-zinc-800">
                <span className="text-[10px] font-bold uppercase text-zinc-400 tracking-wider">Live Commodity Comparison</span>
                <div className="h-24 flex items-end gap-2 mt-2">
                  {compareList.map((commodityKey) => {
                    const state = allStates.find((s) => s.commodity === commodityKey);
                    const value = state?.volatility?.score ?? 0;
                    const height = Math.min(100, Math.max(8, value * 80));
                    return (
                      <div key={commodityKey} className="flex-1 text-center">
                        <div className="mx-auto w-6 rounded-sm" style={{ height: `${height}px`, backgroundColor: '#10b981' }} />
                        <div className="text-[10px] text-zinc-500 mt-2 uppercase">{commodityKey}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Section 9: SEASONAL REPLAY ENGINE */}
          <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-zinc-400 flex items-center gap-2">
              <RotateCcw className="w-3.5 h-3.5 text-emerald-500" />
              <span>Seasonal Replay Engine</span>
            </h3>

            <div className="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-xl space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-zinc-500">Replay step:</span>
                <span className="text-xs font-extrabold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">{currentReplayPoint?.date}</span>
              </div>

              {/* Metrics shifting dynamically during active simulation */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-white dark:bg-zinc-900 p-2.5 rounded-lg border border-zinc-200/60 dark:border-zinc-800/80">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-400">Price response</span>
                  <p className="text-sm font-extrabold mt-0.5">₹{currentReplayPoint?.price}</p>
                </div>
                <div className="bg-white dark:bg-zinc-900 p-2.5 rounded-lg border border-zinc-200/60 dark:border-zinc-800/80">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-400">Mandi Arrivals</span>
                  <p className="text-sm font-extrabold mt-0.5">{currentReplayPoint?.arrivals} MT</p>
                </div>
              </div>

              <div className="bg-white dark:bg-zinc-900 px-3 py-2 rounded-lg border border-zinc-200/60 dark:border-zinc-800/80 flex justify-between items-center">
                <span className="text-[9px] uppercase tracking-wider text-zinc-400">Calculated Regime</span>
                <span className="text-xs font-bold text-emerald-500">{currentReplayPoint?.regime}</span>
              </div>

              {/* Progress timeline bar */}
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-1 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300"
                  style={{ width: `${(replayIndex / (historicalSeries.length - 1)) * 100}%` }}
                />
              </div>

              {/* Media layout dashboard control buttons */}
              <div className="flex items-center justify-between pt-2">
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsReplaying(!isReplaying)}
                    className="p-2 bg-emerald-505 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                  >
                    {isReplaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => {
                      setIsReplaying(false);
                      setReplayIndex(0);
                    }}
                    className="p-2 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-650"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center gap-1.5 bg-zinc-200/40 dark:bg-zinc-900 rounded-lg p-0.5 border border-zinc-150 dark:border-zinc-850">
                  {([1, 2, 3] as const).map((speed) => (
                    <button
                      key={speed}
                      onClick={() => setReplaySpeed(speed)}
                      className={`text-[10px] font-bold px-2 py-1 rounded ${
                        replaySpeed === speed ? 'bg-white dark:bg-zinc-800 shadow-xs' : 'text-zinc-400'
                      }`}
                    >
                      {speed}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN - Price Charts, Timelines, Memory Maps, Seasonality Explorer */}
        <div className="lg:col-span-8 space-y-8">
          
          {/* Section 2: FULL-WIDTH INTERACTIVE PRICE CHART (Hero) */}
          <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Integrated Valuation Graph</span>
                <h3 className="text-lg font-bold tracking-tight">Price Projection Workstation</h3>
              </div>

              {/* Chart Legend */}
              <div className="flex items-center gap-4 text-xs font-semibold text-zinc-500">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-emerald-500" />
                  <span>Historical modal price</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 border-t border-dashed border-emerald-400" />
                  <span>Forecast extension</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 bg-emerald-500/10 rounded-sm" />
                  <span>Uncertainty band</span>
                </div>
              </div>
            </div>

            {/* Interactive SVG Chart Canvas */}
            <div className="relative overflow-visible">
              {svgPoints.length > 0 ? (
                <svg
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  className="w-full h-auto overflow-visible select-none"
                  onMouseMove={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const xRatio = (e.clientX - rect.left) / rect.width;
                    const targetX = xRatio * chartWidth;
                    
                    // Find nearest point
                    let nearest = svgPoints[0];
                    let minDistance = Math.abs(svgPoints[0].x - targetX);
                    
                    svgPoints.forEach((p) => {
                      const dist = Math.abs(p.x - targetX);
                      if (dist < minDistance) {
                        minDistance = dist;
                        nearest = p;
                      }
                    });
                    
                    if (nearest) {
                      setHoveredPoint(nearest);
                      // Translate local SVG coordinates back to relative viewport offsets for premium tooltip placements
                      const tooltipX = (nearest.x / chartWidth) * rect.width;
                      const tooltipY = (nearest.y / chartHeight) * rect.height;
                      setTooltipPos({ x: tooltipX, y: tooltipY });
                    }
                  }}
                  onMouseLeave={() => setHoveredPoint(null)}
                >
                  {/* Horizontal grid guide lines */}
                  {Array.from({ length: 5 }).map((_, i) => {
                    const y = 40 + i * ((chartHeight - 80) / 4);
                    const priceLabel = Math.round(maxPrice - i * (priceRange / 4));
                    return (
                      <g key={i}>
                        <line
                          x1="40"
                          y1={y}
                          x2={chartWidth - 40}
                          y2={y}
                          stroke="rgba(148, 163, 184, 0.08)"
                          strokeDasharray="4"
                        />
                        <text
                          x="30"
                          y={y + 4}
                          fill="rgba(148, 163, 184, 0.4)"
                          fontSize="10"
                          fontWeight="bold"
                          textAnchor="end"
                        >
                          ₹{priceLabel}
                        </text>
                      </g>
                    );
                  })}

                  {/* Shaded Area of uncertainty/confidence band */}
                  <path
                    d={`
                      ${svgPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y - 18}`).join(' ')}
                      L ${svgPoints[svgPoints.length - 1].x} ${svgPoints[svgPoints.length - 1].y + 18}
                      ${svgPoints.slice().reverse().map((p) => `L ${p.x} ${p.y + 18}`).join(' ')}
                      Z
                    `}
                    fill="rgba(16, 185, 129, 0.04)"
                  />

                  {/* Shaded Area underneath the main price line */}
                  <path
                    d={`
                      ${svgPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')}
                      L ${svgPoints[svgPoints.length - 1].x} ${chartHeight - 40}
                      L ${svgPoints[0].x} ${chartHeight - 40}
                      Z
                    `}
                    fill="url(#chartGradient)"
                  />

                  {/* Historical smooth price bezier line */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke="rgba(16, 185, 129, 0.85)"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                  />

                  {/* Forecast Extension smooth projection line */}
                  {forecastPoints.length > 0 && (
                    <path
                      d={`M ${svgPoints[svgPoints.length - 1].x} ${svgPoints[svgPoints.length - 1].y}
                        ${forecastPoints.map((p) => `L ${p.x} ${p.y}`).join(' ')}`}
                      fill="none"
                      stroke="rgba(16, 185, 129, 0.5)"
                      strokeWidth="2.5"
                      strokeDasharray="4 4"
                    />
                  )}

                  {/* Vertical interactive hover guide line */}
                  {hoveredPoint && (
                    <line
                      x1={hoveredPoint.x}
                      y1="40"
                      x2={hoveredPoint.x}
                      y2={chartHeight - 40}
                      stroke="rgba(16, 185, 129, 0.3)"
                      strokeWidth="1.5"
                      strokeDasharray="2"
                    />
                  )}

                  {/* Hover indicator dot */}
                  {hoveredPoint && (
                    <circle
                      cx={hoveredPoint.x}
                      cy={hoveredPoint.y}
                      r="6"
                      fill="rgb(16, 185, 129)"
                      stroke="white"
                      strokeWidth="2.5"
                      className="shadow-sm"
                    />
                  )}

                  {/* Gradients definitions */}
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(16, 185, 129, 0.15)" />
                      <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                    </linearGradient>
                  </defs>
                </svg>
              ) : (
                isInitialLoading ? (
                  <div className="h-64 w-full rounded-lg animate-pulse bg-zinc-100 dark:bg-zinc-800" />
                ) : (
                  <div className="h-64 flex items-center justify-center text-sm text-zinc-400">
                    No historical data available for this market.
                  </div>
                )
              )}

              {/* Premium Hover Interactive Tooltip Box */}
              {hoveredPoint && (
                <div
                  className="absolute pointer-events-none bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3.5 shadow-xl space-y-1 z-30 transition-all duration-75 text-xs"
                  style={{
                    left: `${tooltipPos.x + 16}px`,
                    top: `${tooltipPos.y - 48}px`,
                    transform: 'translate(-50%, -100%)'
                  }}
                >
                  <p className="font-extrabold text-[10px] text-zinc-400 uppercase tracking-widest">{hoveredPoint.data.date}</p>
                  <div className="flex justify-between items-center gap-4">
                    <span className="text-zinc-550 dark:text-zinc-400">Modal Price:</span>
                    <span className="font-extrabold text-zinc-950 dark:text-white">₹{hoveredPoint.data.price}</span>
                  </div>
                  <div className="flex justify-between items-center gap-4">
                    <span className="text-zinc-550 dark:text-zinc-400">Arrival Vol:</span>
                    <span className="font-bold text-zinc-700 dark:text-zinc-350">{hoveredPoint.data.arrivals} MT</span>
                  </div>
                  <div className="pt-1.5 border-t border-zinc-100 dark:border-zinc-800 flex justify-between items-center">
                    <span className="text-[9px] uppercase font-bold text-emerald-500">{hoveredPoint.data.regime}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* SECTION 3: SEASONALITY EXPLORER & SECTION 4: ARRIVAL VS PRICE ANALYZER (Side-by-side or stacked grids) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Seasonality Explorer */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <div>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Seasonality Explorer</span>
                <h3 className="text-sm font-bold tracking-tight">Month-by-Month Trend Performance</h3>
              </div>

              {/* Monthly seasonality index bar chart */}
              <div className="h-40 flex items-end gap-1.5 pt-4">
                {seasonalityIndex.map((val, idx) => {
                  const months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
                  const heightPct = (val / 150) * 100;
                  const isPeak = val === Math.max(...seasonalityIndex);
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                      <div className="relative group w-full h-full flex items-end">
                        <div
                          className={`w-full rounded-sm transition-all duration-300 ${
                            isPeak
                              ? 'bg-emerald-500 dark:bg-emerald-600'
                              : 'bg-zinc-200 hover:bg-zinc-300 dark:bg-zinc-850 dark:hover:bg-zinc-800'
                          }`}
                          style={{ height: `${heightPct}%` }}
                        />
                        {/* Hover tooltip for monthly values */}
                        <div className="absolute opacity-0 group-hover:opacity-100 bg-zinc-900 text-white rounded p-1 text-[9px] bottom-full left-1/2 -translate-x-1/2 mb-1 pointer-events-none font-bold">
                          {val}%
                        </div>
                      </div>
                      <span className={`text-[10px] font-black ${isPeak ? 'text-emerald-500 font-extrabold' : 'text-zinc-400'}`}>
                        {months[idx]}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <span className="font-extrabold text-zinc-900 dark:text-white">Peak Window:</span> September (Festivals & Monsoon constriction). <span className="font-extrabold text-zinc-900 dark:text-white">Trough Window:</span> March (Rabi harvest arrivals).
              </div>
            </div>

            {/* Arrival vs Price Analyzer */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <div>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Cross-Agent Elasticity</span>
                <h3 className="text-sm font-bold tracking-tight">Price Response vs Mandi Arrivals</h3>
              </div>

              {/* Price/Arrival mini correlation plot */}
              <div className="h-40 relative flex items-end justify-between pt-4">
                {/* Horizontal grids */}
                <div className="absolute inset-x-0 bottom-0 h-[1px] bg-zinc-200 dark:bg-zinc-800" />
                <div className="absolute inset-x-0 bottom-1/2 h-[1px] bg-zinc-150 dark:bg-zinc-850/80 stroke-dasharray-2" />
                
                {/* Arrivals column bar overlay with price lines */}
                {historicalSeries.slice(-12).map((pt, idx) => {
                  const arrHeight = (pt.arrivals / 2500) * 110;
                  const priceHeight = ((pt.price - minPrice) / (priceRange || 1)) * 110;
                  return (
                    <div key={idx} className="flex-1 flex flex-col justify-end items-center h-full relative group">
                      {/* Arrivals bar */}
                      <div
                        className="w-3 bg-zinc-200/80 dark:bg-zinc-800/80 rounded-t-xs hover:bg-zinc-300 dark:hover:bg-zinc-700"
                        style={{ height: `${arrHeight}px` }}
                      />
                      {/* Price indicator point */}
                      <div
                        className="absolute w-2 h-2 rounded-full bg-emerald-500 border border-white dark:border-zinc-900 shadow-sm"
                        style={{ bottom: `${priceHeight}px` }}
                      />
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-between items-center text-[10px] pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-sm bg-zinc-200 dark:bg-zinc-800" />
                  <span className="text-zinc-505 text-zinc-500 font-medium">Arrival Volume (MT)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-zinc-505 text-zinc-500 font-medium">Modal Price (₹)</span>
                </div>
                <span className="font-extrabold text-emerald-600">Correlation: -0.74</span>
              </div>
            </div>

          </div>

          {/* SECTION 5: MARKET REGIME HISTORY TIMELINE */}
          <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-6">
            <div>
              <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Macro Trajectory timeline</span>
              <h3 className="text-sm font-bold tracking-tight">Chronological Volatility Regimes</h3>
            </div>

            {/* Horizontal Timeline tracks */}
            <div className="relative pt-2 pb-6">
              <div className="absolute inset-x-0 top-6 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full" />
              
              <div className="relative flex justify-between">
                {[
                  { semester: 'H1 2024', status: 'Stable Expansion', color: 'bg-emerald-500' },
                  { semester: 'H2 2024', status: 'Festival Volatility', color: 'bg-amber-500' },
                  { semester: 'H1 2025', status: 'Supply Shock', color: 'bg-red-500' },
                  { semester: 'H2 2025', status: 'Transitional Stress', color: 'bg-purple-500' },
                  { semester: 'Current Era', status: 'Evolved Stability', color: 'bg-emerald-600' }
                ].map((node, i) => (
                  <div key={i} className="flex flex-col items-center text-center max-w-[100px] relative z-10">
                    <div className={`w-3.5 h-3.5 rounded-full ${node.color} border-2 border-white dark:border-zinc-900 shadow-sm`} />
                    <span className="text-[10px] font-black uppercase tracking-wider text-zinc-400 mt-3">{node.semester}</span>
                    <span className="text-[11px] font-bold text-zinc-800 dark:text-zinc-250 mt-1 whitespace-nowrap">{node.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION 6: PRICE MEMORY MAP & SECTION 8: SIMILAR MARKET PATTERNS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Price Memory Map */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <div>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Position vs History</span>
                <h3 className="text-sm font-bold tracking-tight">Price Memory Envelope</h3>
              </div>

              {/* Horizontal Range Track */}
              <div className="space-y-4 pt-4">
                <div className="relative py-2">
                  <div className="h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full w-full" />
                  
                  {/* Current Position Marker */}
                  <div
                    className="absolute top-0 w-4.5 h-4.5 rounded-full bg-emerald-500 border-2 border-white dark:border-zinc-900 shadow-md flex items-center justify-center cursor-pointer group"
                    style={{ left: '82%' }}
                  >
                    <div className="absolute bottom-full mb-1 opacity-0 group-hover:opacity-100 bg-zinc-900 text-white rounded px-2 py-0.5 text-[9px] font-bold whitespace-nowrap">
                      82nd Percentile
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 text-[10px] font-bold uppercase text-zinc-400 tracking-wider">
                  <div className="text-left">
                    <span>Low</span>
                    <p className="font-extrabold text-zinc-950 dark:text-white mt-0.5">₹1,180</p>
                  </div>
                  <div className="text-center">
                    <span>Median</span>
                    <p className="font-extrabold text-zinc-950 dark:text-white mt-0.5">₹2,400</p>
                  </div>
                  <div className="text-center">
                    <span>Average</span>
                    <p className="font-extrabold text-zinc-950 dark:text-white mt-0.5">₹2,320</p>
                  </div>
                  <div className="text-right">
                    <span>High</span>
                    <p className="font-extrabold text-zinc-950 dark:text-white mt-0.5">₹3,900</p>
                  </div>
                </div>
              </div>

              <div className="text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                Current price of <span className="font-extrabold text-zinc-900 dark:text-white">₹3,200</span> sits higher than <span className="font-extrabold text-emerald-600 dark:text-emerald-400">82%</span> of all observed historical points on the 10-year master record.
              </div>
            </div>

            {/* Similar Market Patterns */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm space-y-4">
              <div>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-400">Pattern Recognition</span>
                <h3 className="text-sm font-bold tracking-tight">Analogous Historical Periods</h3>
              </div>

              <div className="space-y-3">
                {similarPatterns.map((pt, i) => (
                  <div key={i} className="flex justify-between items-center p-2.5 rounded-lg border border-zinc-150 dark:border-zinc-850 bg-zinc-50/50 dark:bg-zinc-950/20 text-xs">
                    <div>
                      <p className="font-extrabold text-zinc-900 dark:text-white">{pt.period}</p>
                      <span className="text-[10px] text-zinc-400 uppercase tracking-wider">{pt.event}</span>
                    </div>

                    <div className="text-right">
                      <p className="font-extrabold text-emerald-600 dark:text-emerald-400">{pt.match}% match</p>
                      <span className={`text-[10px] font-bold ${pt.direction === 'up' ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {pt.move} post-move
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
