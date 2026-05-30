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
  { commodity: 'dry_chillies', mandi_id: 'guntur_apmc' }
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
  
  const TIME_RANGE_OPTIONS = [
    { key: '1D' as const, label: '1D', ms: 24 * 60 * 60 * 1000 },
    { key: '1W' as const, label: '1W', ms: 7 * 24 * 60 * 60 * 1000 },
    { key: '1M' as const, label: '1M', ms: 30 * 24 * 60 * 60 * 1000 },
    { key: '3M' as const, label: '3M', ms: 90 * 24 * 60 * 60 * 1000 },
    { key: '6M' as const, label: '6M', ms: 180 * 24 * 60 * 60 * 1000 },
    { key: '1Y' as const, label: '1Y', ms: 365 * 24 * 60 * 60 * 1000 },
    { key: '3Y' as const, label: '3Y', ms: 3 * 365 * 24 * 60 * 60 * 1000 },
    { key: '5Y' as const, label: '5Y', ms: 5 * 365 * 24 * 60 * 60 * 1000 },
    { key: 'ALL' as const, label: 'ALL', ms: Infinity },
  ];
  type TimeRangeKey = (typeof TIME_RANGE_OPTIONS)[number]['key'];

  // Custom interactive states for Bloomberg/TradingView workstation look
  const [timeRange, setTimeRange] = useState<TimeRangeKey>('1Y');
  const [hoveredPoint, setHoveredPoint] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'dna' | 'narrative' | 'comparison'>('dna');

  // Replay Engine States
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [replaySpeed, setReplaySpeed] = useState<1 | 2 | 3>(1);
  const replayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Comparison Lab States
  const [compareList, setCompareList] = useState<string[]>(['tomato', 'onion', 'potato']);

  const getSeriesForRange = (series: HistoricalSeriesEntry[], range: TimeRangeKey) => {
    if (!series.length) return [];
    if (range === 'ALL') return series;

    const rangeDef = TIME_RANGE_OPTIONS.find((item) => item.key === range);
    if (!rangeDef || !Number.isFinite(rangeDef.ms)) return series;

    const latestTime = new Date(series[series.length - 1].timestamp).getTime();
    const cutoff = latestTime - rangeDef.ms;
    const filtered = series.filter((entry) => new Date(entry.timestamp).getTime() >= cutoff);
    if (filtered.length) return filtered;

    return series.slice(-Math.min(series.length, 60));
  };
  
  // 1. Initial Cache Seeding Mount
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      setIsInitialLoading(true);
      try {
        await marketCache.init(selectedMarket || ALL_MARKETS[0]);
        if (!mounted) return;
        const opts = marketCache.getAvailableOptions();
        setMarketOptions(opts.length ? opts : ALL_MARKETS);
        setSelectedMarket((prev) => {
          if (prev && opts.some((o) => o.commodity === prev.commodity && o.mandi_id === prev.mandi_id)) {
            return prev;
          }
          return opts[0] || ALL_MARKETS[0];
        });
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

  // 2. Selected Market Switch Handler - Realtime cache-to-UI binder
  useEffect(() => {
    if (!selectedMarket) return;

    const selectedKey = `${selectedMarket.commodity}|${selectedMarket.mandi_id}`;
    let isCurrent = true;

    // A. Sync Lookup from Cache first (Instantaneous UI updates - zero spinner!)
    const cachedState = marketCache.getState(selectedMarket.commodity, selectedMarket.mandi_id);
    const cachedHistory = marketCache.getHistory(selectedMarket.commodity, selectedMarket.mandi_id);
    const cachedAnalysis = marketCache.getAnalysis(selectedMarket.commodity, selectedMarket.mandi_id);
    
    setMarketState(cachedState);
    setMarketHistory(cachedHistory || []);
    setMarketAnalysis(cachedAnalysis);
    setDisplaySeries(getSeriesForRange(cachedAnalysis?.historicalSeries ?? [], timeRange));
    setAllStates(marketCache.getAllStates());
    setIsReplaying(false);
    setReplayIndex(0);

    // B. Trigger background API analysis update if stale or not fully generated
    marketCache.loadMarketAnalysis(selectedMarket.commodity, selectedMarket.mandi_id)
      .then((analysis) => {
        if (!isCurrent) return;
        if (analysis) {
          setMarketState(marketCache.getState(selectedMarket.commodity, selectedMarket.mandi_id));
          setMarketHistory(marketCache.getHistory(selectedMarket.commodity, selectedMarket.mandi_id));
          setMarketAnalysis(analysis);
          setDisplaySeries(getSeriesForRange(analysis.historicalSeries, timeRange));
          setAllStates(marketCache.getAllStates());
        }
      })
      .catch((error) => {
        if (!isCurrent) return;
        console.error('MarketCache.loadMarketAnalysis failed', error);
        setError('Unable to refresh market intelligence; showing cached values.');
      });

    // C. Background prefetch of adjacent markets
    marketCache.prefetchAdjacent(selectedMarket);

    return () => {
      isCurrent = false;
    };
  }, [selectedMarket, timeRange]);

  // Derived datasets
  const historicalSeries = displaySeries;
  const seasonalityIndex = marketAnalysis?.seasonalityIndex ?? Array(12).fill(100);
  const dnaMetrics = marketAnalysis?.dnaMetrics ?? [
    { axis: 'Volatility', value: 50, label: 'Live volatility signal' },
    { axis: 'Forecast Stability', value: 50, label: 'Confidence in the latest view' },
    { axis: 'Freshness', value: 75, label: 'Integrity of current intelligence' },
    { axis: 'Momentum', value: 50, label: 'Regime momentum from recent history' },
    { axis: 'Trend Bias', value: 60, label: 'Direction of the latest forecast' },
    { axis: 'Seasonality', value: 80, label: 'Aggregate seasonal pressure' },
  ];

  // Radar chart vector calculation
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

  // Replay player intervals
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

  // Price memory map envelope computations
  const priceMemory = useMemo(() => {
    if (marketAnalysis?.priceMemory) return marketAnalysis.priceMemory;
    const currentPrice = marketState?.price_prediction || 2500;
    return {
      low: currentPrice * 0.65,
      median: currentPrice * 0.95,
      average: currentPrice * 0.98,
      high: currentPrice * 1.45,
      percentile: 72,
      currentPosition: currentPrice
    };
  }, [marketAnalysis, marketState]);

  // Ensemble Deliberation Research Synthesis (Answers: What does the market tell me? no buy/sell directives)
  const researchSynthesis = useMemo(() => {
    if (!marketState) return 'Sourcing fresh market snapshots...';
    
    const commName = marketState.commodity.toUpperCase();
    const trendText = marketState.trend 
      ? `The modal price displays an active ${marketState.trend} projection`
      : 'Prices sit inside a consolidated horizontal range';
    const riskText = marketState.risk_level 
      ? ` with a ${marketState.risk_level.toLowerCase()} systemic risk level`
      : '';
    const regimeText = marketState.regime 
      ? `, mapped directly to a ${marketState.regime.replace(/_/g, ' ').toLowerCase()} volatility envelope`
      : '';
    
    const volScore = marketState.volatility?.score 
      ? `Volatilities are locked at score ${marketState.volatility.score.toFixed(2)}`
      : 'Frictional mandi volatility signals are stable';
    
    const agents = marketState.deliberation?.agents || [];
    const dominant = marketState.deliberation?.dominant_agent_id?.replace('_agent', '').toUpperCase() || 'FORECAST';
    
    const agentsText = agents.length
      ? ` Ensemble arbitration is dominated by the ${dominant} agent, supported by: ${agents.map(a => `${a.agent_id?.replace('_agent', '').toUpperCase()} (${Math.round((a.confidence || 0) * 100)}% conf)`).join(', ')}.`
      : '';
    const contradictions = marketState.deliberation?.contradictions || [];
    const contradictionText = contradictions.length 
      ? ` Cross-agent signaling reveals contradictions: ${contradictions.join('; ')}.`
      : '';
    
    const chaosScore = marketState.deliberation?.chaos_score ?? 0.05;
    const chaosText = chaosScore > 0.35
      ? ` System convergence chaos is slightly elevated at ${chaosScore.toFixed(2)}, reflecting structural market transition stress.`
      : ' Ensemble convergence continuity is high with minimal agent deviation.';

    return `${trendText}${riskText}${regimeText}. ${volScore}.${agentsText}${contradictionText}${chaosText}`;
  }, [marketState]);

  // Macro Volatility Regime Timeline nodes
  const timelineNodes = useMemo(() => {
    const rawNodes = marketAnalysis?.regimeTimeline ?? [];
    if (rawNodes.length === 0) {
      return [
        { time: 'H1 2024', status: 'Stable Expansion', color: 'bg-emerald-500' },
        { time: 'H2 2024', status: 'Festival Volatility', color: 'bg-amber-500' },
        { time: 'H1 2025', status: 'Supply Shock', color: 'bg-red-500' },
        { time: 'H2 2025', status: 'Transitional Stress', color: 'bg-purple-500' },
        { time: 'Current Era', status: marketState?.regime?.replace(/_/g, ' ') || 'Evolved Stability', color: 'bg-emerald-600' }
      ];
    }
    return rawNodes.map((node) => {
      const dateStr = new Date(node.timestamp).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
      let color = 'bg-emerald-500';
      const r = String(node.regime).toUpperCase();
      if (r.includes('STRESS') || r.includes('TRANSITIONAL')) color = 'bg-purple-500';
      else if (r.includes('VOLATILITY') || r.includes('ELEVATED')) color = 'bg-amber-500';
      else if (r.includes('COMPRESSION') || r.includes('SHOCK')) color = 'bg-rose-500';
      else if (r.includes('STABLE') || r.includes('EXPANSION')) color = 'bg-emerald-500';
      
      return {
        time: dateStr,
        status: node.regime.replace(/_/g, ' '),
        color
      };
    });
  }, [marketAnalysis, marketState]);

  // SVG Chart Setup (Workstation Price Projection)
  const chartHeight = 360;
  const chartWidth = 920;
  const prices = historicalSeries.length ? historicalSeries.map((d) => d.price) : [0, 1];
  const minPrice = Math.min(...prices) * 0.95;
  const maxPrice = Math.max(...prices) * 1.08;
  const priceRange = Math.max(1, maxPrice - minPrice);

  const chartBounds = useMemo(() => {
    if (!historicalSeries.length) return { minTs: 0, maxTs: 1, span: 1 };
    const timestamps = historicalSeries.map((d) => new Date(d.timestamp).getTime());
    const minTs = Math.min(...timestamps);
    const maxTs = Math.max(...timestamps);
    return { minTs, maxTs, span: Math.max(1, maxTs - minTs) };
  }, [historicalSeries]);

  const xAxisTicks = useMemo(() => {
    if (!historicalSeries.length) return [];
    const { minTs, span } = chartBounds;
    return [0, 0.25, 0.5, 0.75, 1].map((fraction) => {
      const time = minTs + span * fraction;
      return {
        x: 50 + (chartWidth - 100) * fraction,
        label: new Date(time).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
      };
    });
  }, [chartBounds]);

  const svgPoints = useMemo(() => {
    if (historicalSeries.length === 0) return [];
    const { minTs, span } = chartBounds;
    return historicalSeries.map((d) => {
      const timestamp = new Date(d.timestamp).getTime();
      const x = ((timestamp - minTs) / span) * (chartWidth - 100) + 50;
      const y = chartHeight - ((d.price - minPrice) / priceRange) * (chartHeight - 80) - 50;
      return { x, y, data: d };
    });
  }, [historicalSeries, chartBounds, minPrice, priceRange]);

  // Smooth historical path curve
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

  // Simulation player coupling crosshair/highlight coordinates
  const activePoint = isReplaying ? svgPoints[replayIndex] : hoveredPoint;

  const activeTooltipPos = useMemo(() => {
    if (!activePoint) return { xPct: 0, yPct: 0 };
    return {
      xPct: (activePoint.x / chartWidth) * 100,
      yPct: (activePoint.y / chartHeight) * 100
    };
  }, [activePoint]);

  // Cross-Component synchronized highlight month index
  const hoverMonth = useMemo(() => {
    if (!activePoint) return null;
    return new Date(activePoint.data.timestamp).getMonth();
  }, [activePoint]);

  const recentSeries = useMemo(() => {
    return historicalSeries.slice(-12);
  }, [historicalSeries]);

  const maxArrivalsVal = useMemo(() => {
    return Math.max(...recentSeries.map(pt => pt.arrivals || 0), 100);
  }, [recentSeries]);

  const hoverSeriesIndex = useMemo(() => {
    if (!activePoint) return null;
    return recentSeries.findIndex(pt => pt.timestamp === activePoint.data.timestamp);
  }, [activePoint, recentSeries]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans transition-colors duration-200">
      
      {/* Upper sub-header bar */}
      <div className="border-b border-zinc-800 bg-zinc-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-950/40 text-emerald-450 text-emerald-400 rounded-lg border border-emerald-800/40">
              <Sliders className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">MS-AI TraderOS</h1>
              <p className="text-[10px] uppercase font-bold text-zinc-500 tracking-[0.2em]">Commodity Intelligence & Research Workstation</p>
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
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs font-bold text-white shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
            >
              {marketOptions.map((market) => (
                <option key={`${market.commodity}-${market.mandi_id}`} value={`${market.commodity}|${market.mandi_id}`} className="bg-zinc-900 text-white">
                  {formatLabel(market)}
                </option>
              ))}
            </select>

            <div className="flex items-center rounded-lg border border-zinc-850 bg-zinc-900/60 p-0.5 shadow-sm">
              {TIME_RANGE_OPTIONS.map((range) => (
                <button
                  key={range.key}
                  onClick={() => setTimeRange(range.key)}
                  className={`rounded-md px-2.5 py-1 text-[10px] font-black uppercase transition-all ${
                    timeRange === range.key
                      ? 'bg-zinc-800 text-emerald-400 border border-zinc-700 shadow-sm'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN - Research Summary, DNA Profile, Comparison Lab, Replay Controls */}
        <div className="lg:col-span-4 space-y-8">
          
          {/* Section 1: Market Research Header / Overview info */}
          <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl relative overflow-hidden backdrop-blur-md">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
            <div className="space-y-1">
              <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Research Focus APMC</span>
              <h2 className="text-2xl font-black tracking-tight text-white uppercase">
                {selectedMarket?.commodity}
              </h2>
              <p className="text-[10px] font-extrabold text-emerald-500 uppercase tracking-widest">{selectedMarket?.mandi_id.replace('_apmc', '').replace('_', ' ')} terminal depot</p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 pt-6 border-t border-zinc-800">
              <div>
                <span className="text-[9px] font-black uppercase text-zinc-550 text-zinc-450 tracking-wider">Benchmark price</span>
                <p className="text-lg font-black mt-0.5 text-white">
                  ₹{formatPrice(marketState?.price_prediction)}
                  <span className="text-[10px] text-zinc-500 font-medium ml-1">/ Qtl</span>
                </p>
              </div>
              <div>
                <span className="text-[9px] font-black uppercase text-zinc-550 text-zinc-450 tracking-wider">Active regime</span>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-black text-emerald-400 mt-1 uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  {marketState?.regime?.replace(/_/g, ' ') || 'STABLE'}
                </span>
              </div>
            </div>
          </div>

          {/* TAB SELECTOR FOR DETAILS */}
          <div className="flex border-b border-zinc-800">
            {(['dna', 'narrative', 'comparison'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 pb-3 text-[10px] font-black uppercase tracking-widest transition-all border-b-2 ${
                  activeTab === tab
                    ? 'border-emerald-500 text-emerald-400 font-black'
                    : 'border-transparent text-zinc-500 hover:text-zinc-350'
                }`}
              >
                {tab === 'dna' ? 'Market DNA' : tab === 'narrative' ? 'Research Digest' : 'Comparison Lab'}
              </button>
            ))}
          </div>

          {/* Section 7: MARKET DNA Radar profile */}
          {activeTab === 'dna' && (
            <div className="bg-zinc-900/20 rounded-2xl border border-zinc-800 p-6 shadow-md">
              <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 mb-4 flex items-center justify-between">
                <span>Commodity DNA Profile</span>
                <Info className="w-3.5 h-3.5 text-zinc-600" />
              </h3>

              <div className="flex justify-center my-4">
                <svg width="180" height="180" viewBox="0 0 180 180" className="overflow-visible">
                  {[0.25, 0.5, 0.75, 1.0].map((scale, i) => (
                    <circle
                      key={i}
                      cx="90"
                      cy="90"
                      r={70 * scale}
                      fill="none"
                      stroke="rgba(148, 163, 184, 0.08)"
                      strokeWidth="1"
                    />
                  ))}
                  {Array.from({ length: 6 }).map((_, i) => {
                    const angle = (i * 2 * Math.PI) / 6 - Math.PI / 2;
                    return (
                      <line
                        key={i}
                        x1="90"
                        y1="90"
                        x2={90 + 70 * Math.cos(angle)}
                        y2={90 + 70 * Math.sin(angle)}
                        stroke="rgba(148, 163, 184, 0.08)"
                        strokeWidth="1"
                      />
                    );
                  })}
                  <polygon
                    points={radarPoints.map((p) => `${p.x},${p.y}`).join(' ')}
                    fill="rgba(16, 185, 129, 0.08)"
                    stroke="rgba(16, 185, 129, 0.6)"
                    strokeWidth="2"
                  />
                  {radarPoints.map((p, i) => (
                    <circle key={i} cx={p.x} cy={p.y} r="3" fill="rgb(16, 185, 129)" />
                  ))}
                </svg>
              </div>

              <div className="space-y-3 mt-6">
                {dnaMetrics.map((metric, i) => (
                  <div key={i} className="flex justify-between items-center text-xs">
                    <span className="text-zinc-400 font-bold">{metric.axis}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-zinc-800 h-1 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500" style={{ width: `${metric.value}%` }} />
                      </div>
                      <span className="font-extrabold w-6 text-right text-zinc-300">{metric.value}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 11: ENSEMBLE RESEARCH DIGEST */}
          {activeTab === 'narrative' && (
            <div className="bg-zinc-900/20 rounded-2xl border border-zinc-800 p-6 shadow-md space-y-4">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-emerald-500 animate-pulse" />
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-550 text-zinc-450">Deliberative Synthesis</h3>
              </div>
              
              <div className="text-[11px] leading-relaxed space-y-3.5 text-zinc-350">
                <p>
                  Sourced from the ensemble state of <span className="font-extrabold text-white">{selectedMarket?.commodity.toUpperCase()}</span>.
                </p>
                <p className="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 text-zinc-300 leading-relaxed font-medium">
                  {researchSynthesis}
                </p>
              </div>
            </div>
          )}

          {/* Section 10: COMPARISON LAB */}
          {activeTab === 'comparison' && (
            <div className="bg-zinc-900/20 rounded-2xl border border-zinc-800 p-6 shadow-md space-y-4">
              <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center justify-between">
                <span>Commodity Volatility Matrix</span>
                <ArrowRightLeft className="w-3.5 h-3.5 text-zinc-500" />
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
                        compareList.includes(commodityKey)
                          ? 'border-emerald-500 bg-emerald-950/10'
                          : 'border-zinc-800 hover:bg-zinc-900/40'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${
                          commodityKey === 'tomato' ? 'bg-red-500' : commodityKey === 'onion' ? 'bg-amber-500' : commodityKey === 'potato' ? 'bg-yellow-600' : 'bg-emerald-600'
                        }`} />
                        <span className="text-xs font-bold uppercase">{commodityKey}</span>
                      </div>
                      <div className="text-right text-[10px]">
                        <span className="text-zinc-500">Live volatility: </span>
                        <span className="font-extrabold text-zinc-350">{volatility !== null ? volatility.toFixed(2) : 'N/A'}</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Lab interactive micro chart mapping comparative lines */}
              <div className="pt-4 border-t border-zinc-800">
                <span className="text-[9px] font-black uppercase text-zinc-500 tracking-wider">Comparative Matrix Mapping</span>
                <div className="h-24 flex items-end gap-2 mt-4 pt-2">
                  {compareList.map((commodityKey) => {
                    const state = allStates.find((s) => s.commodity === commodityKey);
                    const value = state?.volatility?.score ?? 0.35;
                    const height = Math.min(100, Math.max(8, value * 80));
                    return (
                      <div key={commodityKey} className="flex-1 text-center">
                        <div className="mx-auto w-4 rounded-sm transition-all duration-500" style={{ height: `${height}px`, backgroundColor: commodityKey === 'tomato' ? '#ef4444' : commodityKey === 'onion' ? '#f59e0b' : '#ca8a04' }} />
                        <div className="text-[8px] font-black text-zinc-500 mt-2 uppercase">{commodityKey}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Section 9: SEASONAL REPLAY ENGINE */}
          <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2 mb-4">
              <RotateCcw className="w-3.5 h-3.5 text-emerald-500" />
              <span>Historical Replay simulation</span>
            </h3>

            <div className="bg-zinc-950 p-4 rounded-xl space-y-4 border border-zinc-900">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-zinc-550 text-zinc-450">Chronological Step:</span>
                <span className="text-xs font-black text-emerald-400 uppercase tracking-widest">{currentReplayPoint?.date ?? '—'}</span>
              </div>

              {/* Metrics shifting dynamically during active simulation */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-800">
                  <span className="text-[8px] uppercase font-bold tracking-wider text-zinc-500">Price step</span>
                  <p className="text-xs font-extrabold mt-0.5 text-white">₹{currentReplayPoint?.price ?? '—'}</p>
                </div>
                <div className="bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-800">
                  <span className="text-[8px] uppercase font-bold tracking-wider text-zinc-500">Arrivals step</span>
                  <p className="text-xs font-extrabold mt-0.5 text-white">{(currentReplayPoint?.arrivals || 0).toFixed(0)} MT</p>
                </div>
              </div>

              <div className="bg-zinc-900/30 px-3 py-2 rounded-lg border border-zinc-800/80 flex justify-between items-center">
                <span className="text-[8px] uppercase font-bold tracking-wider text-zinc-500">Vol Regime</span>
                <span className="text-[9px] uppercase font-black text-emerald-400 tracking-widest">{currentReplayPoint?.regime?.replace(/_/g, ' ') ?? 'UNKNOWN'}</span>
              </div>

              {/* Progress timeline bar */}
              <div className="w-full bg-zinc-850 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300"
                  style={{ width: `${(replayIndex / (historicalSeries.length - 1 || 1)) * 100}%` }}
                />
              </div>

              {/* Media layout dashboard control buttons */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsReplaying(!isReplaying)}
                    className="p-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors shadow-lg cursor-pointer"
                  >
                    {isReplaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => {
                      setIsReplaying(false);
                      setReplayIndex(0);
                    }}
                    className="p-2 border border-zinc-800 rounded-lg hover:bg-zinc-900 text-zinc-400 transition-colors cursor-pointer"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center gap-1.5 bg-zinc-900 rounded-lg p-0.5 border border-zinc-800">
                  {([1, 2, 3] as const).map((speed) => (
                    <button
                      key={speed}
                      onClick={() => setReplaySpeed(speed)}
                      className={`text-[9px] font-black px-2 py-1 rounded transition-all ${
                        replaySpeed === speed ? 'bg-zinc-800 text-emerald-400 font-extrabold' : 'text-zinc-500'
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
          <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-2xl relative">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Integrated Valuation Graph</span>
                <h3 className="text-lg font-black tracking-tight text-white">Price Projection Workstation</h3>
              </div>

              {/* Chart Legend */}
              <div className="flex items-center gap-4 text-[10px] font-extrabold text-zinc-400 tracking-wide uppercase">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-emerald-500" />
                  <span>Historical rate</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-zinc-700" />
                  <span>Volume snapshot</span>
                </div>
              </div>
            </div>

            {/* Interactive SVG Chart Canvas */}
            <div className="relative overflow-visible select-none">
              {svgPoints.length > 0 ? (
                <svg
                  viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                  className="w-full h-auto overflow-visible select-none cursor-crosshair"
                  onMouseMove={(e) => {
                    if (isReplaying) return; // Replay overrides hover crosshair
                    const rect = e.currentTarget.getBoundingClientRect();
                    const xRatio = (e.clientX - rect.left) / rect.width;
                    const targetX = xRatio * chartWidth;
                    
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
                    }
                  }}
                  onMouseLeave={() => setHoveredPoint(null)}
                >
                  {/* Horizontal grid guide lines */}
                  {Array.from({ length: 5 }).map((_, i) => {
                    const y = 40 + i * ((chartHeight - 90) / 4);
                    const priceLabel = Math.round(maxPrice - i * (priceRange / 4));
                    return (
                      <g key={i}>
                        <line
                          x1="50"
                          y1={y}
                          x2={chartWidth - 50}
                          y2={y}
                          stroke="rgba(148, 163, 184, 0.04)"
                          strokeWidth="1"
                        />
                        <text
                          x="38"
                          y={y + 3.5}
                          fill="rgba(148, 163, 184, 0.35)"
                          fontSize="9"
                          fontWeight="black"
                          textAnchor="end"
                        >
                          ₹{priceLabel}
                        </text>
                      </g>
                    );
                  })}

                  {/* Shaded Area of uncertainty/confidence band (Widening) */}
                  {/* X-axis time markers */}
                  {xAxisTicks.map((tick, i) => (
                    <g key={i}>
                      <line
                        x1={tick.x}
                        y1={chartHeight - 50}
                        x2={tick.x}
                        y2={chartHeight - 46}
                        stroke="rgba(148, 163, 184, 0.3)"
                        strokeWidth="1"
                      />
                      <text
                        x={tick.x}
                        y={chartHeight - 30}
                        fill="rgba(148, 163, 184, 0.7)"
                        fontSize="9"
                        fontWeight="600"
                        textAnchor="middle"
                      >
                        {tick.label}
                      </text>
                    </g>
                  ))}

                  {/* Shaded Area underneath the main price line */}
                  <path
                    d={`
                      ${svgPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')}
                      L ${svgPoints[svgPoints.length - 1].x} ${chartHeight - 50}
                      L ${svgPoints[0].x} ${chartHeight - 50}
                      Z
                    `}
                    fill="url(#chartGradientDark)"
                  />

                  {/* Historical smooth price bezier line */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke="rgba(16, 185, 129, 0.85)"
                    strokeWidth="3.2"
                    strokeLinecap="round"
                  />

                  {/* Crosshair guide lines (TradingView style annotation) */}
                  {activePoint && (
                    <>
                      {/* Vertical crosshair */}
                      <line
                        x1={activePoint.x}
                        y1="40"
                        x2={activePoint.x}
                        y2={chartHeight - 50}
                        stroke="rgba(16, 185, 129, 0.45)"
                        strokeWidth="1.2"
                        strokeDasharray="3 3"
                      />
                      {/* Horizontal crosshair */}
                      <line
                        x1="50"
                        y1={activePoint.y}
                        x2={chartWidth - 50}
                        y2={activePoint.y}
                        stroke="rgba(16, 185, 129, 0.45)"
                        strokeWidth="1.2"
                        strokeDasharray="3 3"
                      />
                      {/* Y-axis price Green badge */}
                      <g transform={`translate(${chartWidth - 45}, ${activePoint.y - 7.5})`}>
                        <rect
                          x="-5"
                          y="0"
                          width="55"
                          height="15"
                          rx="3"
                          fill="#10b981"
                        />
                        <text
                          x="22.5"
                          y="10.5"
                          fill="white"
                          fontSize="9"
                          fontWeight="black"
                          textAnchor="middle"
                        >
                          ₹{Math.round(activePoint.data.price)}
                        </text>
                      </g>
                      {/* X-axis date Slate badge */}
                      <g transform={`translate(${activePoint.x - 35}, ${chartHeight - 45})`}>
                        <rect
                          x="0"
                          y="-5"
                          width="70"
                          height="15"
                          rx="3"
                          fill="#1f2937"
                          stroke="#374151"
                          strokeWidth="1"
                        />
                        <text
                          x="35"
                          y="5.5"
                          fill="white"
                          fontSize="9"
                          fontWeight="black"
                          textAnchor="middle"
                        >
                          {activePoint.data.date}
                        </text>
                      </g>
                      {/* Interactive hover glowing dot */}
                      <circle
                        cx={activePoint.x}
                        cy={activePoint.y}
                        r="6"
                        fill="rgb(16, 185, 129)"
                        stroke="white"
                        strokeWidth="2"
                        className="shadow-xl"
                      />
                    </>
                  )}

                  {/* Gradients definitions */}
                  <defs>
                    <linearGradient id="chartGradientDark" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(16, 185, 129, 0.15)" />
                      <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                    </linearGradient>
                  </defs>
                </svg>
              ) : (
                isInitialLoading ? (
                  <div className="h-64 w-full rounded-2xl animate-pulse bg-zinc-800/40" />
                ) : (
                  <div className="h-64 flex items-center justify-center text-sm text-zinc-500 border border-dashed border-zinc-800 rounded-2xl">
                    No historical snapshots seeded. Launch cognition generator.
                  </div>
                )
              )}

              {/* Premium Hover Interactive Responsive Tooltip Box */}
              {activePoint && (
                <div
                  className="absolute pointer-events-none bg-zinc-950/95 border border-zinc-800 rounded-xl p-3.5 shadow-2xl space-y-1 z-30 transition-all duration-75 text-xs text-white"
                  style={{
                    left: `${activeTooltipPos.xPct}%`,
                    top: `${activeTooltipPos.yPct}%`,
                    transform: 'translate(-50%, -106%)'
                  }}
                >
                  <p className="font-extrabold text-[9px] text-zinc-500 uppercase tracking-widest">{activePoint.data.date}</p>
                  <div className="flex justify-between items-center gap-6">
                    <span className="text-zinc-400">Modal Price:</span>
                    <span className="font-black text-white">₹{formatPrice(activePoint.data.price)}</span>
                  </div>
                  <div className="flex justify-between items-center gap-6">
                    <span className="text-zinc-400">Arrival Vol:</span>
                    <span className="font-extrabold text-zinc-300">{(activePoint.data.arrivals || 0).toFixed(0)} MT</span>
                  </div>
                  <div className="pt-1.5 border-t border-zinc-850 flex justify-between items-center">
                    <span className="text-[9px] uppercase font-black text-emerald-400 tracking-wider">
                      {activePoint.data.regime?.replace(/_/g, ' ') || 'STABLE'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* SECTION 3: SEASONALITY EXPLORER & SECTION 4: ARRIVAL VS PRICE ANALYZER (Side-by-side grids) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Seasonality Explorer */}
            <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl space-y-4">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Seasonality Explorer</span>
                <h3 className="text-sm font-black tracking-tight text-white">Month-by-Month Trend Performance</h3>
              </div>

              {/* Monthly seasonality index bar chart */}
              <div className="h-40 flex items-end gap-1.5 pt-4">
                {seasonalityIndex.map((val, idx) => {
                  const months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
                  const heightPct = (val / Math.max(...seasonalityIndex, 1)) * 100;
                  const isPeak = val === Math.max(...seasonalityIndex);
                  const isHoveredMonth = idx === hoverMonth;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                      <div className="relative group w-full h-full flex items-end">
                        <div
                          className={`w-full rounded-sm transition-all duration-300 ${
                            isPeak
                              ? 'bg-emerald-500'
                              : isHoveredMonth
                              ? 'bg-emerald-400 shadow-lg shadow-emerald-500/20 scale-x-110 h-full border border-emerald-300/30'
                              : 'bg-zinc-800 hover:bg-zinc-700'
                          }`}
                          style={{ height: `${heightPct}%` }}
                        />
                        {/* Hover tooltip for monthly values */}
                        <div className="absolute opacity-0 group-hover:opacity-100 bg-zinc-950 text-white rounded px-1.5 py-0.5 text-[9px] bottom-full left-1/2 -translate-x-1/2 mb-1 pointer-events-none font-bold border border-zinc-800 whitespace-nowrap">
                          {val}%
                        </div>
                      </div>
                      <span className={`text-[9px] font-black ${isPeak ? 'text-emerald-400 font-extrabold' : isHoveredMonth ? 'text-emerald-400' : 'text-zinc-500'}`}>
                        {months[idx]}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="text-[10px] leading-relaxed text-zinc-500 pt-2 border-t border-zinc-800">
                <span className="font-black text-zinc-400">Seasonal Peak Month:</span> <span className="font-extrabold text-emerald-400">{marketAnalysis?.seasonalityPeakMonth || 'September'}</span>. <span className="font-black text-zinc-400">Trough Month:</span> <span className="font-extrabold text-zinc-400">{marketAnalysis?.seasonalityTroughMonth || 'March'}</span>. (Sourced dynamically from master series)
              </div>
            </div>

            {/* Arrival vs Price Analyzer */}
            <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl space-y-4">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Cross-Agent Elasticity</span>
                <h3 className="text-sm font-black tracking-tight text-white">Price Response vs Mandi Arrivals</h3>
              </div>

              {/* Price/Arrival mini correlation plot */}
              <div className="h-40 relative flex items-end justify-between pt-4 overflow-visible">
                <div className="absolute inset-x-0 bottom-0 h-[1px] bg-zinc-800" />
                <div className="absolute inset-x-0 bottom-1/2 h-[1px] bg-zinc-850/50 border-t border-dashed border-zinc-800" />
                
                {recentSeries.map((pt, idx) => {
                  const arrHeight = ((pt.arrivals || 0) / maxArrivalsVal) * 115;
                  const priceHeight = ((pt.price - minPrice) / (priceRange || 1)) * 115;
                  const isHoveredSeriesPt = idx === hoverSeriesIndex;
                  return (
                    <div key={idx} className="flex-1 flex flex-col justify-end items-center h-full relative group">
                      <div
                        className={`w-3.5 rounded-t-xs hover:bg-zinc-700 transition-all ${
                          isHoveredSeriesPt
                            ? 'bg-emerald-500/80 shadow-md shadow-emerald-500/10'
                            : 'bg-zinc-800/80'
                        }`}
                        style={{ height: `${arrHeight}px` }}
                      />
                      <div
                        className={`absolute w-2 h-2 rounded-full border border-zinc-950 shadow-sm transition-all duration-300 ${
                          isHoveredSeriesPt
                            ? 'bg-emerald-400 scale-150 shadow-emerald-500/30 shadow-lg'
                            : 'bg-emerald-500'
                        }`}
                        style={{ bottom: `${priceHeight}px` }}
                      />
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-between items-center text-[9px] font-bold pt-2 border-t border-zinc-800 uppercase text-zinc-500 tracking-wider">
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-xs bg-zinc-800" />
                  <span>Arrival (MT)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>Modal Price (₹)</span>
                </div>
                <span className="font-extrabold text-emerald-400">Pearson: {marketAnalysis?.correlation?.arrivalPriceCorrelation ?? '-0.74'}</span>
              </div>
            </div>

          </div>

          {/* SECTION 5: MARKET REGIME HISTORY TIMELINE */}
          <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl space-y-6">
            <div>
              <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Macro Trajectory timeline</span>
              <h3 className="text-sm font-black tracking-tight text-white">Chronological Volatility Regimes</h3>
            </div>

            {/* Horizontal Timeline tracks */}
            <div className="relative pt-2 pb-6">
              <div className="absolute inset-x-0 top-6 h-1 bg-zinc-800 rounded-full" />
              
              <div className="relative flex justify-between">
                {timelineNodes.map((node, i) => (
                  <div key={i} className="flex flex-col items-center text-center max-w-[100px] relative z-10">
                    <div className={`w-3.5 h-3.5 rounded-full ${node.color} border-2 border-zinc-900 shadow-md`} />
                    <span className="text-[9px] font-black uppercase tracking-wider text-zinc-500 mt-3">{node.time}</span>
                    <span className="text-[10px] font-black text-zinc-350 mt-1 whitespace-nowrap uppercase tracking-wider">{node.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION 6: PRICE MEMORY MAP & SECTION 8: SIMILAR MARKET PATTERNS */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Price Memory Map */}
            <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl space-y-4">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Position vs History</span>
                <h3 className="text-sm font-black tracking-tight text-white">Price Memory Envelope</h3>
              </div>

              {/* Horizontal Range Track */}
              <div className="space-y-4 pt-4">
                <div className="relative py-2">
                  <div className="h-1.5 bg-zinc-800 rounded-full w-full" />
                  
                  {/* Current Position Marker */}
                  <div
                    className="absolute top-0.5 w-4 h-4 rounded-full bg-emerald-500 border-2 border-zinc-950 shadow-lg flex items-center justify-center cursor-pointer group hover:scale-125 transition-all"
                    style={{ left: `${priceMemory.percentile}%` }}
                  >
                    <div className="absolute bottom-full mb-1.5 opacity-0 group-hover:opacity-100 bg-zinc-950 border border-zinc-800 text-white rounded-md px-2 py-0.5 text-[8px] font-black whitespace-nowrap">
                      {priceMemory.percentile}th Percentile
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 text-[9px] font-bold uppercase text-zinc-500 tracking-wider">
                  <div className="text-left">
                    <span>Low</span>
                    <p className="font-black text-white mt-0.5">₹{formatPrice(priceMemory.low)}</p>
                  </div>
                  <div className="text-center">
                    <span>Median</span>
                    <p className="font-black text-white mt-0.5">₹{formatPrice(priceMemory.median)}</p>
                  </div>
                  <div className="text-center">
                    <span>Average</span>
                    <p className="font-black text-white mt-0.5">₹{formatPrice(priceMemory.average)}</p>
                  </div>
                  <div className="text-right">
                    <span>High</span>
                    <p className="font-black text-white mt-0.5">₹{formatPrice(priceMemory.high)}</p>
                  </div>
                </div>
              </div>

              <div className="text-[10px] leading-relaxed text-zinc-500 pt-3 border-t border-zinc-800">
                Current price of <span className="font-extrabold text-zinc-350">₹{formatPrice(marketState?.price_prediction)}</span> sits higher than <span className="font-black text-emerald-400">{priceMemory.percentile}%</span> of all observed historical points on the master record.
              </div>
            </div>

            {/* Similar Market Patterns */}
            <div className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-6 shadow-xl space-y-4">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Pattern Recognition</span>
                <h3 className="text-sm font-black tracking-tight text-white">Analogous Historical Periods</h3>
              </div>

              <div className="space-y-3">
                {similarPatterns.length > 0 ? (
                  similarPatterns.map((pt, i) => (
                    <div key={i} className="flex justify-between items-center p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/20 text-xs">
                      <div>
                        <p className="font-black text-white">{pt.period}</p>
                        <span className="text-[9px] text-zinc-500 uppercase tracking-widest">{pt.event}</span>
                      </div>

                      <div className="text-right">
                        <p className="font-black text-emerald-400">{pt.match}% match</p>
                        <span className={`text-[9px] font-black uppercase tracking-wider ${pt.direction === 'up' ? 'text-emerald-400' : 'text-rose-500'}`}>
                          {pt.move} post-move
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-32 flex items-center justify-center text-[10px] text-zinc-550 border border-dashed border-zinc-850 rounded-xl">
                    Analyzing analog engine trajectories...
                  </div>
                )}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
