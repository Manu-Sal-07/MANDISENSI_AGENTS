'use client';

import { useEffect, useMemo, useState } from 'react';
import { mandiApi } from '@/services/api';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bolt,
  CircleDot,
  Clock3,
  Compass,
  Eye,
  Funnel,
  Globe2,
  Layers,
  MapPin,
  Shield,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

const SCENARIOS = [
  { id: 'arrival_increase', label: 'Arrival Increase' },
  { id: 'arrival_decrease', label: 'Arrival Decrease' },
  { id: 'volatility_spike', label: 'Volatility Spike' },
  { id: 'volatility_collapse', label: 'Volatility Collapse' },
  { id: 'demand_surge', label: 'Demand Surge' },
  { id: 'demand_contract', label: 'Demand Contraction' },
  { id: 'external_shock', label: 'External Shock' },
];

type MarketState = {
  commodity: string;
  mandi_id: string;
  timestamp: string;
  price_prediction?: number;
  confidence?: {
    score?: number;
    stability?: number;
    decay_rate?: number;
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
  directives?: Array<{ primary_directive: string; urgency: string; reasoning: string; confidence_at_synthesis?: number }>;
  forecast_arrivals?: number;
  trend?: string;
  deliberation?: {
    agents?: Array<{ agent_id?: string; signal?: string; confidence?: number; weight?: number; metadata?: Record<string, any> }>;
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
  historical_analogs?: Array<{ timestamp?: string; similarity?: number; regime?: string; directive?: string }>;
};

type ScenarioProjection = {
  name: string;
  price: number;
  confidence: number;
  regime: string;
  risk: string;
  resilience: number;
  narrative: string;
};

const formatMarketLabel = (state: MarketState) =>
  `${state.commodity.toUpperCase()} • ${state.mandi_id.replace('_apmc', '').toUpperCase()}`;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const buildScenarioProjection = (state: MarketState, scenario: string): ScenarioProjection => {
  const basePrice = state.price_prediction ?? 0;
  const baseConfidence = state.confidence?.score ?? 0.45;
  const baseRisk = state.risk_level ?? 'MEDIUM';
  const forecast = state.forecast_arrivals ?? 0;
  const volatility = state.volatility?.score ?? 0.5;

  const diff = (multiplier: number) => clamp(basePrice * multiplier, -12, 12);
  const confidenceShift = (delta: number) => clamp(baseConfidence + delta, 0.05, 0.98);

  switch (scenario) {
    case 'arrival_increase':
      return {
        name: 'Arrival Increase',
        price: basePrice + diff(0.25) - forecast * 0.02,
        confidence: confidenceShift(0.07),
        regime: volatility > 0.7 ? 'ELEVATED_VOLATILITY' : 'STABLE_EXPANSION',
        risk: basePrice > 0 ? 'MEDIUM' : 'HIGH',
        resilience: clamp(75 - volatility * 20, 15, 90),
        narrative: 'Extra arrivals amplify current dynamics and reveal where hidden supply pressure will force a regime test.',
      };
    case 'arrival_decrease':
      return {
        name: 'Arrival Decrease',
        price: basePrice - diff(0.35),
        confidence: confidenceShift(-0.08),
        regime: 'RECOVERY_STABILIZATION',
        risk: basePrice < 0 ? 'HIGH' : 'MEDIUM',
        resilience: clamp(65 - volatility * 25, 10, 80),
        narrative: 'Sharp removal of arrivals triggers a transition test and exposes structural strength in demand.',
      };
    case 'volatility_spike':
      return {
        name: 'Volatility Spike',
        price: basePrice + diff(0.5),
        confidence: confidenceShift(-0.18),
        regime: 'ELEVATED_VOLATILITY',
        risk: 'CRITICAL',
        resilience: clamp(40 - volatility * 15, 5, 60),
        narrative: 'A volatility pulse fractures the signal and surfaces where the market is most fragile.',
      };
    case 'volatility_collapse':
      return {
        name: 'Volatility Collapse',
        price: basePrice + diff(0.12),
        confidence: confidenceShift(0.12),
        regime: 'STABLE_EXPANSION',
        risk: basePrice > 0 ? 'LOW' : 'MEDIUM',
        resilience: clamp(85 - forecast * 8, 40, 98),
        narrative: 'Quieter volatility consolidates the opinion and reveals latent confidence in the twin.',
      };
    case 'demand_surge':
      return {
        name: 'Demand Surge',
        price: basePrice + diff(0.55),
        confidence: confidenceShift(0.05),
        regime: 'RECOVERY_STABILIZATION',
        risk: 'MEDIUM',
        resilience: clamp(70 - volatility * 10, 20, 88),
        narrative: 'A demand shock re-prices the opportunity and surfaces how quickly conviction can strengthen.',
      };
    case 'demand_contract':
      return {
        name: 'Demand Contraction',
        price: basePrice - diff(0.5),
        confidence: confidenceShift(-0.12),
        regime: 'TRANSITIONAL_STRESS',
        risk: 'HIGH',
        resilience: clamp(45 - volatility * 10, 10, 70),
        narrative: 'Demand evaporation stresses the market and reveals the weak points in the existing regime.',
      };
    case 'external_shock':
      return {
        name: 'External Shock',
        price: basePrice + (basePrice >= 0 ? diff(0.4) : diff(-0.4)),
        confidence: confidenceShift(-0.2),
        regime: 'TRANSITIONAL_STRESS',
        risk: 'CRITICAL',
        resilience: clamp(35 - volatility * 12, 5, 60),
        narrative: 'A shock event fractures consensus and forces the digital twin to reveal its worst-case trajectory.',
      };
    default:
      return {
        name: 'Baseline',
        price: basePrice,
        confidence: baseConfidence,
        regime: state.regime ?? 'STABLE_EXPANSION',
        risk: baseRisk,
        resilience: clamp(70 - volatility * 15, 15, 92),
        narrative: 'Current market intelligence baseline used for comparative discovery.',
      };
  }
};

const deriveHeatScore = (value: number) => Math.round(clamp(value * 100, 0, 100));

const IntelligenceLabPage = () => {
  const [allStates, setAllStates] = useState<MarketState[]>([]);
  const [selectedState, setSelectedState] = useState<MarketState | null>(null);
  const [marketState, setMarketState] = useState<MarketState | null>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('arrival_increase');
  const [simulationStatus, setSimulationStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadIntelligence = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const [states, mems] = await Promise.all([
          mandiApi.getCognitionStates(),
          mandiApi.getCognitionMemories(),
        ]);

        const normalizedStates = Array.isArray(states) ? states : [];
        setAllStates(normalizedStates);

        if (normalizedStates.length > 0) {
          const firstState = normalizedStates[0];
          setSelectedState(firstState);
        }

        setMemories(Array.isArray(mems) ? mems.slice(0, 8) : []);
      } catch (e) {
        setError('Unable to load Intelligence Lab data.');
      } finally {
        setIsLoading(false);
      }
    };

    loadIntelligence();
  }, []);

  useEffect(() => {
    if (!selectedState) {
      setMarketState(null);
      return;
    }

    const loadState = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const selected = await mandiApi.getMarketState(selectedState.commodity, selectedState.mandi_id);
        setMarketState(selected);
      } catch (e) {
        setError('Unable to load selected market intelligence.');
        setMarketState(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadState();
  }, [selectedState]);

  const baselineProjection = useMemo(() => {
    if (!marketState) return null;
    return buildScenarioProjection(marketState, 'baseline');
  }, [marketState]);

  const selectedProjection = useMemo(() => {
    if (!marketState) return null;
    return buildScenarioProjection(marketState, selectedScenario);
  }, [marketState, selectedScenario]);

  const topBoard = useMemo(() => {
    if (!allStates.length) return [];

    const trendState = allStates.reduce((best, item) => {
      const value = Math.abs(item.price_prediction ?? 0);
      return value > Math.abs(best.price_prediction ?? 0) ? item : best;
    }, allStates[0]);

    const convictionState = allStates.reduce((best, item) => {
      const score = item.confidence?.score ?? 0;
      return score > (best.confidence?.score ?? 0) ? item : best;
    }, allStates[0]);

    const qualityState = allStates.reduce((best, item) => {
      const quality = item.freshness?.integrity_score ?? 0;
      return quality > (best.freshness?.integrity_score ?? 0) ? item : best;
    }, allStates[0]);

    const unusualState = allStates.reduce((best, item) => {
      const volatility = item.volatility?.score ?? 0;
      const discord = Math.abs((item.price_prediction ?? 0) - ((item.directives?.[0]?.confidence_at_synthesis ?? 0) * 100));
      return volatility + discord > ((best.volatility?.score ?? 0) + Math.abs((best.price_prediction ?? 0) - ((best.directives?.[0]?.confidence_at_synthesis ?? 0) * 100))) ? item : best;
    }, allStates[0]);

    const opportunityState = allStates.reduce((best, item) => {
      const score = Math.abs(item.price_prediction ?? 0) * (item.confidence?.score ?? 0) * ((item.freshness?.integrity_score ?? 0) + 0.15);
      const bestScore = Math.abs(best.price_prediction ?? 0) * (best.confidence?.score ?? 0) * ((best.freshness?.integrity_score ?? 0) + 0.15);
      return score > bestScore ? item : best;
    }, allStates[0]);

    return [
      {
        label: 'Hidden Opportunity',
        value: formatMarketLabel(opportunityState),
        note: `Signal: ${(opportunityState.price_prediction ?? 0).toFixed(1)}%`,
        tone: 'emerald',
      },
      {
        label: 'Emerging Trend',
        value: formatMarketLabel(trendState),
        note: `Trend: ${(trendState.price_prediction ?? 0).toFixed(1)}%`,
        tone: 'sky',
      },
      {
        label: 'Highest Conviction',
        value: formatMarketLabel(convictionState),
        note: `Confidence: ${Math.round((convictionState.confidence?.score ?? 0) * 100)}%`,
        tone: 'violet',
      },
      {
        label: 'Unusual Behavior',
        value: formatMarketLabel(unusualState),
        note: `Volatility: ${((unusualState.volatility?.score ?? 0) * 100).toFixed(0)}%`,
        tone: 'amber',
      },
      {
        label: 'Intelligence Quality',
        value: formatMarketLabel(qualityState),
        note: `Integrity: ${Math.round((qualityState.freshness?.integrity_score ?? 0) * 100)}%`,
        tone: 'slate',
      },
    ];
  }, [allStates]);

  const hiddenScanner = useMemo(() => {
    if (!allStates.length) return [];
    return [...allStates]
      .map((state) => {
        const strength = Math.abs(state.price_prediction ?? 0);
        const neglect = 1 - (state.confidence?.score ?? 0);
        const catalyst = (state.volatility?.score ?? 0) + ((state.forecast_arrivals ?? 0) / 20);
        return {
          label: formatMarketLabel(state),
          opportunity: Math.round(strength * 10 + neglect * 15),
          neglectScore: Math.round(neglect * 100),
          expectedUpside: `${(state.price_prediction ?? 0).toFixed(1)}%`,
          catalyst: `${catalyst.toFixed(1)} / 10`,
          confidence: Math.round((state.confidence?.score ?? 0) * 100),
        };
      })
      .sort((a, b) => b.opportunity - a.opportunity)
      .slice(0, 4);
  }, [allStates]);

  const conflictSpectrum = useMemo(() => {
    const agents = marketState?.deliberation?.agents || [];
    return agents.map((agent) => ({
      name: agent.agent_id || 'anonymous',
      signal: agent.signal || 'neutral',
      confidence: Math.round((agent.confidence ?? 0) * 100),
      weight: Math.round((agent.weight ?? 0) * 100),
    }));
  }, [marketState]);

  const convictionClusters = useMemo(() => {
    if (!allStates.length) return [];
    const sample = [...allStates].slice(0, 9);
    return sample.map((state) => ({
      label: state.commodity.toUpperCase(),
      location: state.mandi_id.replace('_apmc', '').toUpperCase(),
      conviction: Math.round((state.confidence?.score ?? 0) * 100),
      intensity: Math.abs(state.price_prediction ?? 0),
    }));
  }, [allStates]);

  const collectiveIndex = useMemo(() => {
    if (!allStates.length) return { quality: 0, clarity: 0, readiness: 0, agreement: 0 };
    const quality = allStates.reduce((sum, state) => sum + (state.freshness?.integrity_score ?? 0), 0) / allStates.length;
    const clarity = allStates.reduce((sum, state) => sum + (state.confidence?.stability ?? 0.4), 0) / allStates.length;
    const agreement = allStates.filter((state) => {
      const directive = state.directives?.[0]?.primary_directive?.toUpperCase() ?? '';
      const price = state.price_prediction ?? 0;
      return (directive.includes('SELL') && price < 0) || (directive.includes('BUY') && price > 0) || (directive.includes('HOLD') && Math.abs(price) < 1);
    }).length / allStates.length;
    return {
      quality: Math.round(quality * 100),
      clarity: Math.round(clarity * 100),
      readiness: Math.round((quality * 0.4 + clarity * 0.4 + agreement * 100 * 0.2)),
      agreement: Math.round(agreement * 100),
    };
  }, [allStates]);

  const anomalyRadar = useMemo(() => {
    return allStates
      .filter((state) => (state.volatility?.score ?? 0) > 0.75 || Math.abs(state.price_prediction ?? 0) > 7 || (state.freshness?.integrity_score ?? 1) < 0.5)
      .slice(0, 4)
      .map((state) => ({
        title: formatMarketLabel(state),
        reason: state.volatility?.score ?? 0 > 0.75 ? 'Volatility surge' : Math.abs(state.price_prediction ?? 0) > 7 ? 'Large directional signal' : 'Integrity risk',
        impact: Math.round(((state.volatility?.score ?? 0) + Math.abs(state.price_prediction ?? 0) / 15) * 100),
      }));
  }, [allStates]);

  const signalGenome = useMemo(() => {
    if (!marketState) return [];
    const seasonality = marketState.metadata?.seasonality_score ?? 0.6;
    const arrivalSensitivity = clamp((marketState.forecast_arrivals ?? 0) / 10, 0, 1);
    const volatilityExposure = clamp(marketState.volatility?.score ?? 0.5, 0, 1);
    const regimeSensitivity = marketState.metadata?.regime_sensitivity ?? 0.6;
    const confidenceStability = clamp(marketState.confidence?.stability ?? 0.55, 0, 1);
    const shockExposure = marketState.metadata?.shock_exposure ?? 0.5;

    return [
      { label: 'Seasonality', value: Math.round(seasonality * 100) },
      { label: 'Arrival', value: Math.round(arrivalSensitivity * 100) },
      { label: 'Volatility', value: Math.round(volatilityExposure * 100) },
      { label: 'Regime', value: Math.round(regimeSensitivity * 100) },
      { label: 'Stability', value: Math.round(confidenceStability * 100) },
      { label: 'Shock', value: Math.round(shockExposure * 100) },
    ];
  }, [marketState]);

  const lifecycleState = useMemo(() => {
    if (!marketState) return 'Discovery';
    const confidence = marketState.confidence?.score ?? 0;
    const integrity = marketState.freshness?.integrity_score ?? 0;
    if (confidence > 0.75 && integrity > 0.75) return 'Expansion';
    if (confidence > 0.55) return 'Validation';
    if ((marketState.price_prediction ?? 0) > 3) return 'Maturity';
    return 'Discovery';
  }, [marketState]);

  const marketNarrative = useMemo(() => {
    if (!marketState) return 'Select a market to reveal the hidden narrative and structural thesis behind the signal.';
    const directive = marketState.directives?.[0]?.primary_directive || 'HOLD';
    const analog = marketState.historical_analogs?.[0];
    return `The Intelligence Lab has detected ${marketState.regime || 'a regime'} profile in ${marketState.commodity} @ ${marketState.mandi_id}. ${directive} appears to be the dominant signal, supported by ${Math.round((marketState.confidence?.score ?? 0) * 100)}% conviction and ${Math.round((marketState.freshness?.integrity_score ?? 0) * 100)}% intelligence quality. ${analog ? `A historical analog from ${new Date(analog.timestamp || '').toLocaleDateString()} matches with ${((analog.similarity ?? 0) * 100).toFixed(0)}% similarity.` : 'No close analog was found in the short-term archive.'}`;
  }, [marketState]);

  const handleSimulationLaunch = async () => {
    if (!marketState) return;

    try {
      setSimulationStatus('Launching institutional simulation...');
      await mandiApi.simulateMarketScenario(marketState.commodity, marketState.mandi_id, selectedScenario, {
        horizon: '7d',
      });
      setSimulationStatus('Simulation queued. Watch for the cognition stream update.');
    } catch (e) {
      console.error(e);
      setSimulationStatus('Simulation request failed.');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">
      <div className="mx-auto max-w-[1480px] px-4 py-8">
        <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-4 py-2 text-sm font-semibold uppercase tracking-[0.32em] text-emerald-700 dark:text-emerald-200">
              <Sparkles className="h-4 w-4" />
              Intelligence Lab
            </div>
            <div className="space-y-3 max-w-3xl">
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">Market Discovery Engine</h1>
              <p className="max-w-2xl text-lg leading-8 text-zinc-600 dark:text-zinc-400">
                Uncover hidden structural intelligence, simulate mission-critical stress scenarios, and compare the selected mandi against history and the collective market brain.
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-3xl border border-zinc-200 bg-white/85 p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[11px] uppercase tracking-[0.4em] text-zinc-500">Markets tracked</p>
              <p className="mt-3 text-2xl font-black">{allStates.length}</p>
            </div>
            <div className="rounded-3xl border border-zinc-200 bg-white/85 p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[11px] uppercase tracking-[0.4em] text-zinc-500">Selected intelligence</p>
              <p className="mt-3 text-2xl font-black">{marketState ? formatMarketLabel(marketState) : '--'}</p>
            </div>
            <div className="rounded-3xl border border-zinc-200 bg-white/85 p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[11px] uppercase tracking-[0.4em] text-zinc-500">Memory assets</p>
              <p className="mt-3 text-2xl font-black">{memories.length}</p>
            </div>
          </div>
          <div className="mt-6 rounded-[2rem] border border-zinc-200 bg-white/90 p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
            <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Market selector</p>
            <select
              value={selectedState ? `${selectedState.commodity}|${selectedState.mandi_id}` : ''}
              onChange={(event) => {
                const [commodity, mandi_id] = event.target.value.split('|');
                const next = allStates.find((item) => item.commodity === commodity && item.mandi_id === mandi_id);
                if (next) setSelectedState(next);
              }}
              className="mt-3 w-full rounded-3xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-emerald-500 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100"
            >
              {allStates.map((state) => (
                <option key={`${state.commodity}-${state.mandi_id}`} value={`${state.commodity}|${state.mandi_id}`}>
                  {formatMarketLabel(state)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <section className="mb-10 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {topBoard.map((item) => (
            <div key={item.label} className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.4em] text-zinc-500">{item.label}</p>
              <p className="mt-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">{item.value}</p>
              <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">{item.note}</p>
            </div>
          ))}
        </section>

        <div className="grid gap-6 xl:grid-cols-[0.62fr_0.38fr]">
          <div className="space-y-6">
            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Future State Simulator</p>
                  <h2 className="mt-3 text-2xl font-bold">Play the counterfactuals</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  {SCENARIOS.map((scenario) => (
                    <button
                      key={scenario.id}
                      onClick={() => setSelectedScenario(scenario.id)}
                      className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${selectedScenario === scenario.id ? 'border-emerald-500 bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200' : 'border-zinc-200 bg-zinc-100 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300'}`}
                    >
                      {scenario.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {['price', 'confidence', 'resilience'].map((metric) => {
                  const value = selectedProjection ? selectedProjection[metric as keyof ScenarioProjection] : '--';
                  const suffix = metric === 'confidence' ? '%' : metric === 'price' ? '%' : '';
                  return (
                    <div key={metric} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                      <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">{metric.replace(/^[a-z]/, (c) => c.toUpperCase())}</p>
                      <p className="mt-3 text-3xl font-black text-zinc-900 dark:text-zinc-100">{typeof value === 'number' ? `${value.toFixed(1)}${suffix}` : value}</p>
                    </div>
                  );
                })}
              </div>

              <div className="mt-6 grid gap-3 rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Scenario narrative</p>
                <p className="text-sm leading-7 text-zinc-600 dark:text-zinc-400">{selectedProjection?.narrative || 'Choose a mission-critical stress case to see the latent intelligence shift.'}</p>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  onClick={handleSimulationLaunch}
                  disabled={!marketState}
                  className="rounded-3xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
                >
                  Launch Institutional Simulation
                </button>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{simulationStatus || 'Simulation runs asynchronously and will update cognition state when ready.'}</p>
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Digital Twin Market</p>
                  <h2 className="mt-3 text-2xl font-bold">Market mission control</h2>
                </div>
                <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs uppercase tracking-[0.35em] text-zinc-500 dark:bg-zinc-900">Live model</span>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="rounded-3xl bg-zinc-100 p-5 dark:bg-zinc-900">
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Regime posture</p>
                  <p className="mt-3 text-xl font-semibold text-zinc-900 dark:text-zinc-100">{marketState?.regime || '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-5 dark:bg-zinc-900">
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Risk posture</p>
                  <p className="mt-3 text-xl font-semibold text-zinc-900 dark:text-zinc-100">{marketState?.risk_level || '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-5 dark:bg-zinc-900">
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Supply pressure</p>
                  <p className="mt-3 text-xl font-semibold text-zinc-900 dark:text-zinc-100">{marketState ? `${marketState.forecast_arrivals?.toFixed(1) ?? '--'}%` : '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-5 dark:bg-zinc-900">
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Volatility posture</p>
                  <p className="mt-3 text-xl font-semibold text-zinc-900 dark:text-zinc-100">{marketState?.volatility?.regime || '--'}</p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 rounded-3xl bg-zinc-100 p-5 text-sm text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                <div className="flex items-center justify-between">
                  <span>Market health</span>
                  <span>{marketState ? `${Math.round((marketState.freshness?.integrity_score ?? 0) * 100)}%` : '--'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Resilience</span>
                  <span>{selectedProjection ? `${selectedProjection.resilience}%` : '--'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Consensus signal</span>
                  <span>{marketState?.directives?.[0]?.primary_directive || '--'}</span>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Stress Test Engine</p>
                  <h2 className="mt-3 text-2xl font-bold">Resilience audit</h2>
                </div>
                <div className="text-xs uppercase tracking-[0.35em] text-zinc-500">Institutional grade</div>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {['supply shock', 'arrival surge', 'demand collapse', 'policy disturbance'].map((label, index) => (
                  <div key={label} className="rounded-3xl border border-zinc-200 bg-zinc-100 p-4 dark:border-zinc-800 dark:bg-zinc-900">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{label}</p>
                    <p className="mt-3 text-3xl font-black text-emerald-700 dark:text-emerald-300">{marketState ? `${clamp(80 - index * 8 - ((marketState.volatility?.score ?? 0) * 15), 18, 90).toFixed(0)}%` : '--'}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.35em] text-zinc-500">Resilience score</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-3xl bg-zinc-100 p-4 text-sm text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                <p className="font-semibold text-zinc-900 dark:text-zinc-100">Weakness</p>
                <p className="mt-2">{marketState ? (marketState.volatility?.score ?? 0) > 0.7 ? 'Volatility is the primary pressure point in this market.' : 'Structural confidence is the most fragile dimension.' : 'No market selected.'}</p>
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Alternate Reality Engine</p>
              <h2 className="mt-3 text-2xl font-bold">Historical analogs</h2>
              <div className="mt-6 space-y-4">
                {marketState?.historical_analogs?.length ? (
                  marketState.historical_analogs.slice(0, 3).map((analog, index) => (
                    <div key={index} className="rounded-3xl border border-zinc-200 bg-zinc-100 p-4 dark:border-zinc-800 dark:bg-zinc-900">
                      <div className="flex items-center justify-between gap-3 text-sm text-zinc-500">
                        <span>{new Date(analog.timestamp || '').toLocaleDateString() || 'Unknown date'}</span>
                        <span>{((analog.similarity ?? 0) * 100).toFixed(0)}%</span>
                      </div>
                      <p className="mt-3 font-semibold text-zinc-900 dark:text-zinc-100">{analog.regime || 'Unknown regime'}</p>
                      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">Directive: {analog.directive || 'HOLD'}</p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl bg-zinc-100 p-4 text-sm text-zinc-500 dark:bg-zinc-900">No clear historical analogs are available for this market state.</div>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Opportunity Decay</p>
              <h2 className="mt-3 text-2xl font-bold">Time window analysis</h2>
              <div className="mt-6 space-y-3 text-sm text-zinc-600 dark:text-zinc-400">
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Remaining window</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? `${clamp(30 - ((marketState.freshness?.integrity_score ?? 1) * 15), 3, 30).toFixed(0)} days` : '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Opportunity strength</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? `${Math.round(Math.abs(marketState.price_prediction ?? 0) * 11)} / 100` : '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Urgency</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? (marketState.freshness?.integrity_score ?? 0) > 0.7 ? 'Elevated' : 'Critical' : '--'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Confidence Evolution</p>
              <h2 className="mt-3 text-2xl font-bold">Signal durability</h2>
              <div className="mt-6 space-y-3 text-sm text-zinc-600 dark:text-zinc-400">
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Current conviction</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? `${Math.round((marketState.confidence?.score ?? 0) * 100)}%` : '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Stability</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? `${Math.round((marketState.confidence?.stability ?? 0) * 100)}%` : '--'}</p>
                </div>
                <div className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                  <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">Trend momentum</p>
                  <p className="mt-2 text-xl font-semibold">{marketState ? marketState.trend || '--' : '--'}</p>
                </div>
              </div>
            </div>
          </aside>
        </div>

        <section className="mb-10 grid gap-6 xl:grid-cols-[0.7fr_0.3fr]">
          <div className="space-y-6">
            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Intelligence Conflict Detector</p>
                  <h2 className="mt-3 text-2xl font-bold">Consensus network</h2>
                </div>
                <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs uppercase tracking-[0.35em] text-zinc-500 dark:bg-zinc-900">Signal alignment</span>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {conflictSpectrum.map((agent) => (
                  <div key={agent.name} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{agent.name}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.35em] text-zinc-500">Signal</p>
                    <p className="text-lg font-bold">{agent.signal}</p>
                    <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                      <span>Confidence</span>
                      <span>{agent.confidence}%</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-zinc-200 dark:bg-zinc-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${agent.confidence}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Signal Genome</p>
              <h2 className="mt-3 text-2xl font-bold">Fingerprint</h2>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {signalGenome.map((item) => (
                  <div key={item.label} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                    <p className="text-xs uppercase tracking-[0.35em] text-zinc-500">{item.label}</p>
                    <p className="mt-3 text-2xl font-black text-zinc-900 dark:text-zinc-100">{item.value}%</p>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${item.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Conviction Map</p>
              <h2 className="mt-3 text-2xl font-bold">Where the market is most reliable</h2>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {convictionClusters.map((cluster) => (
                  <div key={`${cluster.label}-${cluster.location}`} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{cluster.label}</p>
                    <p className="text-xs text-zinc-500">{cluster.location}</p>
                    <div className="mt-4 flex items-center justify-between text-sm text-zinc-500">
                      <span>Confidence</span>
                      <span>{cluster.conviction}%</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
                      <div className="h-full rounded-full bg-sky-500" style={{ width: `${cluster.conviction}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Collective Intelligence Index</p>
              <h2 className="mt-3 text-2xl font-bold">Market clarity</h2>
              <div className="mt-6 space-y-4">
                {[
                  { name: 'Intelligence Quality', value: `${collectiveIndex.quality}%` },
                  { name: 'Signal Clarity', value: `${collectiveIndex.clarity}%` },
                  { name: 'Consensus Agreement', value: `${collectiveIndex.agreement}%` },
                  { name: 'Readiness', value: `${collectiveIndex.readiness}%` },
                ].map((item) => (
                  <div key={item.name} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                    <div className="flex items-center justify-between text-sm text-zinc-500">
                      <span>{item.name}</span>
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100">{item.value}</span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: item.value }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Market Memory Engine</p>
              <h2 className="mt-3 text-2xl font-bold">Archive evidence</h2>
              <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">Most recent strategic memories from the institutional archive.</p>
              <div className="mt-6 space-y-3 text-sm">
                {memories.length ? (
                  memories.slice(0, 4).map((memory) => (
                    <div key={memory.id} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                      <p className="font-semibold text-zinc-900 dark:text-zinc-100">{memory.type || 'Memory'}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.35em] text-zinc-500">{memory.commodity} / {memory.scenario || 'standard'}</p>
                      <p className="mt-2 text-zinc-500 dark:text-zinc-400">{new Date(memory.timestamp).toLocaleString()}</p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl bg-zinc-100 p-4 text-zinc-500 dark:bg-zinc-900">No archive memories loaded yet.</div>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Black Swan Radar</p>
                  <h2 className="mt-3 text-2xl font-bold">Anomaly detection</h2>
                </div>
                <div className="rounded-full bg-rose-500/10 px-3 py-1 text-xs uppercase tracking-[0.35em] text-rose-600 dark:text-rose-300">Flagged</div>
              </div>

              <div className="mt-6 space-y-3">
                {anomalyRadar.length ? (
                  anomalyRadar.map((item) => (
                    <div key={item.title} className="rounded-3xl bg-zinc-100 p-4 dark:bg-zinc-900">
                      <div className="flex items-center justify-between gap-3 text-sm text-zinc-500">
                        <span>{item.title}</span>
                        <span>{item.impact}%</span>
                      </div>
                      <p className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{item.reason}</p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-3xl bg-zinc-100 p-4 text-sm text-zinc-500 dark:bg-zinc-900">No active anomalies detected in the current intelligence snapshot.</div>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.36em] text-zinc-500">Market Narrative Lab</p>
              <h2 className="mt-3 text-2xl font-bold">Explainer thesis</h2>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-zinc-100 px-4 py-2 text-xs uppercase tracking-[0.35em] text-zinc-500 dark:bg-zinc-900">
              <CircleDot className="h-4 w-4" />
              Evidence-backed
            </div>
          </div>
          <p className="mt-6 max-w-4xl text-sm leading-7 text-zinc-600 dark:text-zinc-400">{marketNarrative}</p>
        </section>

        {error && (
          <div className="mt-8 rounded-[2rem] border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="mt-8 rounded-[2rem] border border-zinc-200 bg-white/90 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950/80">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading Intelligence Lab data...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntelligenceLabPage;
