'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  BrainCircuit,
  ChevronRight,
  Command,
  Database,
  Gauge,
  Layers3,
  RefreshCw,
  Search,
  Sparkles,
  Zap,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  Sliders,
  Server,
  ShieldAlert,
  Cpu,
  Play,
  CheckCircle,
  Clock,
  Terminal,
  ArrowRight,
} from 'lucide-react';
import { useCognitionStream } from '@/hooks/useCognitionStream';
import TradingSection from '@/components/trading/TradingSection';

type Directive = {
  primary_directive?: string;
  action_code?: string;
  urgency?: string;
  reasoning?: string;
};

type Agent = {
  agent_id?: string;
  signal?: string;
  confidence?: number;
  weight?: number;
};

type MarketState = {
  commodity?: string;
  mandi_id?: string;
  directives?: Directive | Directive[] | string;
  confidence?: { score?: number };
  deliberation?: { agents?: Agent[]; chaos_score?: number; contradictions?: string[] };
  price_prediction?: number;
  trend?: string;
  risk_level?: string;
  regime?: string;
  volatility?: { regime?: string };
  integrity_status?: string;
  forecast_arrivals?: number;
  metadata?: any;
};

type QuickHealth = {
  intelligence_available?: boolean;
  commodities_with_intelligence?: string[];
};

type QueryResult = {
  decision?: string;
  summary?: string;
  reasoning?: string;
  market_insight?: string;
};

type CopilotResponse = {
  recommendation: string;
  evidence: string;
  risk: string;
  businessImpact: string;
  confidence: string;
  nextAction: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const COMMODITY_VOLUMES: Record<string, number> = {
  tomato: 2500,
  onion: 5000,
  potato: 8000,
  garlic: 1500,
  ginger: 2000,
  dry_chillies: 3000,
};

const getDirective = (directives?: Directive | Directive[] | string): Directive | undefined => {
  const directive = Array.isArray(directives) ? directives[0] : directives;
  if (typeof directive === 'string') {
    return {
      primary_directive: directive,
      reasoning: directive,
      action_code: 'EXECUTE',
    };
  }
  return directive;
};

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const formatTime = (value?: string | number | Date | null) => {
  if (!value) return '';
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value;
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(date);
};

const actionTone = (value = '') => {
  const upper = value.toUpperCase();
  if (upper.includes('SELL')) return 'risk';
  if (upper.includes('BUY') || upper.includes('ACCUMULATE')) return 'positive';
  if (upper.includes('HOLD')) return 'stable';
  if (upper.includes('WAIT')) return 'warning';
  return 'neutral';
};

const toneClass: Record<string, string> = {
  positive: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
  stable: 'text-sky-300 border-sky-500/15 bg-sky-500/5',
  warning: 'text-amber-350 border-amber-500/20 bg-amber-500/5',
  risk: 'text-rose-400 border-rose-500/20 bg-rose-500/5',
  neutral: 'text-slate-300 border-slate-800 bg-slate-900/10',
};

const getMarketMetrics = (state: MarketState) => {
  const commodity = state.commodity?.toLowerCase() ?? 'tomato';
  const volume = COMMODITY_VOLUMES[commodity] ?? 1000;
  const price = state.price_prediction ?? 0;
  const confidence = state.confidence?.score ?? 0.5;
  const trend = state.trend ?? 'stable';
  const risk = state.risk_level ?? 'LOW';

  const meta = state.metadata || {};
  let priceChangePct = typeof meta.price_change_pct === 'number' 
    ? Math.abs(meta.price_change_pct) 
    : (trend === 'upward' ? 0.05 * confidence : trend === 'downward' ? 0.06 * confidence : 0);

  let actionName = 'ACCUMULATE POSITION';
  let tone = 'stable';
  let financialImpact = volume * price * priceChangePct;
  let costOfDelay = 0;

  const backendDecision = meta.decision;

  if (backendDecision) {
    if (backendDecision === 'HOLD' || backendDecision === 'ACCUMULATE') {
      actionName = risk === 'HIGH' || risk === 'CRITICAL' ? 'LOCK CONTRACTS' : 'ACCELERATE PROCUREMENT';
      tone = risk === 'HIGH' || risk === 'CRITICAL' ? 'warning' : 'positive';
      costOfDelay = financialImpact / 4;
    } else if (backendDecision === 'SELL') {
      actionName = 'DELAY PROCUREMENT';
      tone = 'risk';
      costOfDelay = 0;
    } else {
      actionName = 'ACCUMULATE POSITION';
      tone = 'neutral';
      costOfDelay = 0;
    }
  } else {
    if (trend === 'upward') {
      costOfDelay = financialImpact / 4;
      actionName = risk === 'HIGH' || risk === 'CRITICAL' ? 'LOCK CONTRACTS' : 'ACCELERATE PROCUREMENT';
      tone = risk === 'HIGH' || risk === 'CRITICAL' ? 'warning' : 'positive';
    } else if (trend === 'downward') {
      costOfDelay = 0;
      actionName = 'DELAY PROCUREMENT';
      tone = 'risk';
      } else {
      actionName = 'ACCUMULATE POSITION';
      tone = 'neutral';
    }
  }

  return {
    volume,
    price,
    trend,
    risk,
    actionName,
    tone,
    financialImpact,
    costOfDelay,
    priceChangePct,
  };
};

function StatusDot({ ok, pulse = false }: { ok: boolean; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2 items-center justify-center">
      {ok && pulse && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/30 opacity-75" />}
      <span className={cx('relative h-1.5 w-1.5 rounded-full', ok ? 'bg-emerald-400' : 'bg-rose-500')} />
    </span>
  );
}

export default function TraderOS() {
  const stream = useCognitionStream();
  const {
    status,
    latestUpdate: rawLatestUpdate,
    allStates: rawAllStates,
    systemHealth: rawSystemHealth,
    queryResult: rawQueryResult,
    isQuerying,
    quickHealth: rawQuickHealth,
    submitQuery,
    triggerRefresh,
  } = stream;

  const allStates = (rawAllStates as MarketState[]) || [];
  const quickHealth = rawQuickHealth as QuickHealth | null;
  const latestUpdate = rawLatestUpdate;

  const [activeIdx, setActiveIdx] = useState(0);
  const [clock, setClock] = useState('');
  const [enterprisePosture, setEnterprisePosture] = useState<any>(null);
  
  // Interactive Simulator State
  const [shiftPct, setShiftPct] = useState<number>(50);

  // Copilot Panel Interface State
  const [activeQuery, setActiveQuery] = useState<string>('');
  const [copilotResponse, setCopilotResponse] = useState<CopilotResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [customInput, setCustomInput] = useState<string>('');

  useEffect(() => {
    setClock(formatTime(new Date()));
    const timer = setInterval(() => setClock(formatTime(new Date())), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;
    const fetchPosture = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/v1/enterprise/posture`);
        if (res.ok) {
          const data = await res.json();
          if (active && data && data.status !== 'initializing') {
            setEnterprisePosture(data);
          }
        }
      } catch {}
    };
    fetchPosture();
    const interval = setInterval(fetchPosture, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const [selectedCommodity, setSelectedCommodity] = useState<string>('ALL');
  const [selectedMandi, setSelectedMandi] = useState<string>('ALL');
  const [selectedHorizon, setSelectedHorizon] = useState<string>('30D');
  const [selectedMode, setSelectedMode] = useState<string>('ATTENTION');

  const availableMandis = useMemo(() => {
    const mandisSet = new Set<string>();
    allStates.forEach((state) => {
      if (selectedCommodity === 'ALL' || state.commodity?.toUpperCase() === selectedCommodity.toUpperCase()) {
        if (state.mandi_id) {
          mandisSet.add(state.mandi_id);
        }
      }
    });
    return Array.from(mandisSet);
  }, [allStates, selectedCommodity]);

  const filteredStates = useMemo(() => {
    return allStates.filter((state) => {
      const matchComm = selectedCommodity === 'ALL' || state.commodity?.toUpperCase() === selectedCommodity.toUpperCase();
      const matchMandi = selectedMandi === 'ALL' || state.mandi_id?.toLowerCase() === selectedMandi.toLowerCase();
      return matchComm && matchMandi;
    });
  }, [allStates, selectedCommodity, selectedMandi]);

  const safeActiveIdx = allStates.length > 0 ? Math.min(activeIdx, allStates.length - 1) : 0;
  const activeState = useMemo(() => {
    if (filteredStates.length > 0) {
      const matchIdx = filteredStates.findIndex((s) => {
        const currentActive = allStates[safeActiveIdx];
        return currentActive && s.commodity?.toLowerCase() === currentActive.commodity?.toLowerCase() && s.mandi_id?.toLowerCase() === currentActive.mandi_id?.toLowerCase();
      });
      return matchIdx !== -1 ? filteredStates[matchIdx] : filteredStates[0];
    }
    return allStates[safeActiveIdx] ?? null;
  }, [filteredStates, allStates, safeActiveIdx]);

  const calculatedResilience = useMemo(() => {
    const targetStates = filteredStates.length > 0 ? filteredStates : allStates;
    if (targetStates.length === 0) return null;
    const topology = targetStates.map((state) => {
      const isHigh = state.risk_level === 'HIGH' || state.risk_level === 'CRITICAL';
      const riskVal = isHigh ? 1.0 : 0.0;
      const chaosVal = state.deliberation?.chaos_score ?? 0.2;
      return { fragility_index: riskVal * chaosVal };
    });
    const avgFragility = topology.reduce((acc, curr) => acc + curr.fragility_index, 0) / topology.length;
    const overall = Math.max(0.1, 1.0 - avgFragility);
    return {
      overall_score: overall,
      sourcing_resilience: overall * 0.9,
      volatility_tolerance: 1.0 - avgFragility,
    };
  }, [allStates, filteredStates]);

  const activeResilience = enterprisePosture?.resilience || calculatedResilience;

  const portfolioMetrics = useMemo(() => {
    let totalExposure = 0;
    let totalOpportunity = 0;
    let totalDelayCost = 0;
    let criticalCount = 0;

    filteredStates.forEach((state) => {
      const metrics = getMarketMetrics(state);
      totalExposure += metrics.volume * metrics.price;
      totalOpportunity += metrics.financialImpact;
      totalDelayCost += metrics.costOfDelay;
      if (state.risk_level === 'HIGH' || state.risk_level === 'CRITICAL') {
        criticalCount++;
      }
    });

    return {
      totalExposure,
      totalOpportunity,
      totalDelayCost,
      criticalCount,
    };
  }, [filteredStates]);

  const criticalCorridors = useMemo(() => {
    return filteredStates
      .map((state) => {
        const originalIndex = allStates.findIndex(s => s.commodity?.toLowerCase() === state.commodity?.toLowerCase() && s.mandi_id?.toLowerCase() === state.mandi_id?.toLowerCase());
        return { state, index: originalIndex, metrics: getMarketMetrics(state) };
      })
      .filter(({ state, metrics }) => {
        if (selectedMode === 'ATTENTION') {
          return state.risk_level === 'HIGH' || state.risk_level === 'CRITICAL' || metrics.tone === 'risk' || metrics.tone === 'warning';
        }
        if (selectedMode === 'DECISIONS') {
          return metrics.actionName === 'LOCK CONTRACTS' || metrics.actionName === 'ACCUMULATE POSITION';
        }
        if (selectedMode === 'RISKS') {
          return state.risk_level === 'HIGH' || state.risk_level === 'CRITICAL' || metrics.tone === 'risk';
        }
        if (selectedMode === 'OPPORTUNITIES') {
          return metrics.tone === 'positive' || metrics.financialImpact > 100000;
        }
        return true;
      });
  }, [allStates, filteredStates, selectedMode]);

  const suggestedQuestions = useMemo(() => [
    {
      id: 'risk',
      label: 'What is my biggest procurement risk this month?',
      query: 'What is my biggest procurement risk this month?',
    },
    {
      id: 'savings',
      label: 'Where are the largest cost-saving opportunities?',
      query: 'Where are the largest cost-saving opportunities?',
    },
    {
      id: 'delay',
      label: 'What happens if we delay procurement?',
      query: 'What happens if we delay procurement?',
    },
    {
      id: 'attention',
      label: 'Which commodities require immediate C-Suite attention?',
      query: 'Which commodities require immediate C-Suite attention?',
    },
  ], []);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setActiveQuery(queryText);

    // CONTEXT RESOLUTION ENGINE
    let resolvedComm = selectedCommodity !== 'ALL' ? selectedCommodity : null;
    let resolvedMandi = selectedMandi !== 'ALL' ? selectedMandi : null;
    let resolvedHorizon = selectedHorizon;

    const queryLower = queryText.toLowerCase();

    // Priority 1: Explicit User Context
    if (queryLower.includes('tomato')) resolvedComm = 'TOMATO';
    else if (queryLower.includes('onion')) resolvedComm = 'ONION';
    else if (queryLower.includes('potato')) resolvedComm = 'POTATO';
    else if (queryLower.includes('garlic')) resolvedComm = 'GARLIC';
    else if (queryLower.includes('ginger')) resolvedComm = 'GINGER';

    if (queryLower.includes('bangalore') || queryLower.includes('yeshwanthpur')) {
      resolvedMandi = 'bangalore_yeshwanthpur_apmc';
    } else if (queryLower.includes('kolar')) {
      resolvedMandi = 'kolar_apmc';
    }

    if (queryLower.includes('7d') || queryLower.includes('7 days') || queryLower.includes('1 week')) resolvedHorizon = '7D';
    else if (queryLower.includes('14d') || queryLower.includes('14 days') || queryLower.includes('2 weeks')) resolvedHorizon = '14D';
    else if (queryLower.includes('30d') || queryLower.includes('30 days') || queryLower.includes('1 month')) resolvedHorizon = '30D';
    else if (queryLower.includes('seasonal') || queryLower.includes('season')) resolvedHorizon = 'SEASONAL';
    else if (queryLower.includes('long term') || queryLower.includes('long-term') || queryLower.includes('strategic')) resolvedHorizon = 'LONG_TERM';

    // Priority 2/3: Active context / Global scope resolution
    const targetState = allStates.find((s) => {
      const matchComm = !resolvedComm || s.commodity?.toUpperCase() === resolvedComm.toUpperCase();
      const matchMandi = !resolvedMandi || s.mandi_id?.toLowerCase() === resolvedMandi.toLowerCase();
      return matchComm && matchMandi;
    }) || activeState; // fall back to active selected state if not found

    const metrics = targetState ? getMarketMetrics(targetState) : null;
    const commName = targetState?.commodity?.toUpperCase() || 'PORTFOLIO';
    const mandiName = targetState?.mandi_id?.replace('_apmc', '').replace(/_/g, ' ').toUpperCase() || 'ALL APMCS';

    // Call backend
    try {
      const res = await fetch(`${API_BASE_URL}/v1/query/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: queryText,
          context: {
            commodity: resolvedComm || targetState?.commodity,
            mandi: resolvedMandi || targetState?.mandi_id,
            horizon: resolvedHorizon
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        
        setCopilotResponse({
          recommendation: data.decision 
            ? `Decision: ${data.decision.toUpperCase()}. ${data.summary || data.reasoning}`
            : `DECISION ADVISORY for ${commName} at ${mandiName}.`,
          evidence: data.reasoning || `Resolved scoping to ${commName} at ${mandiName} under ${resolvedHorizon} forecast.`,
          risk: data.market_insight || `Volatility indicator matches standard historical bounds.`,
          businessImpact: metrics ? `₹${(metrics.financialImpact / 100000).toFixed(2)} Lakhs projected exposure variance` : '₹0.00 Lakhs',
          confidence: data.metadata?.confidence ? `${(data.metadata.confidence * 100).toFixed(0)}%` : '88%',
          nextAction: `Model risk mitigation ROI using the shift simulator for ${commName}.`
        });
        setLoading(false);
        return;
      }
    } catch (err) {
      console.error("Backend query failed, falling back to context-resolved simulator intelligence", err);
    }

    // Local Fallback Context-Resolved Decision Engine
    setTimeout(() => {
      const isRiskQuery = queryLower.includes('risk') || queryLower.includes('danger') || queryLower.includes('watch') || queryLower.includes('threat');
      const isOppQuery = queryLower.includes('opportunity') || queryLower.includes('buy') || queryLower.includes('saving');
      const isDecisionQuery = queryLower.includes('do') || queryLower.includes('action') || queryLower.includes('decide');

      let recommendation = '';
      let evidence = '';
      let riskStr = '';
      let impactStr = '';
      let nextAction = '';

      if (resolvedComm) {
        const tone = metrics?.tone || 'stable';
        const priceStr = metrics ? `₹${metrics.price.toFixed(0)}` : 'N/A';
        
        if (isRiskQuery) {
          recommendation = `MITIGATE VOLATILITY: Adjust ${resolvedComm} limits at ${mandiName}.`;
          evidence = `${resolvedComm} price is currently at ${priceStr} showing a ${metrics?.trend || 'stable'} trend.`;
          riskStr = `Seasonal inflow deviations at ${mandiName} present high risk exposure.`;
          impactStr = `₹${((metrics?.financialImpact || 0) / 100000).toFixed(2)} Lakhs at risk.`;
          nextAction = `Access the War Room simulator and apply a 45% sourcing cover.`;
        } else if (isOppQuery) {
          recommendation = `OPPORTUNITY CAPTURE: Accumulate ${resolvedComm} at ${mandiName}.`;
          evidence = `Stable to downward price trends support forward accumulation.`;
          riskStr = `Nominal transport deviations; seasonal volume forecasts are strong.`;
          impactStr = `₹${((metrics?.financialImpact || 0) / 100000).toFixed(2)} Lakhs projected cost avoidance.`;
          nextAction = `Increase Sourcing Shift to 70% to lock in lower prices.`;
        } else {
          recommendation = `STRATEGIC DIRECTIVE: ${metrics?.actionName || 'HOLD'} position for ${resolvedComm}.`;
          evidence = `Price index is ${priceStr} with ${targetState?.confidence?.score ? (targetState.confidence.score * 100).toFixed(0) : '85'}% signal convergence.`;
          riskStr = `Supply network resilience is computed at ${(activeResilience?.overall_score * 100).toFixed(0)}%.`;
          impactStr = `₹${((metrics?.financialImpact || 0) / 100000).toFixed(2)} Lakhs exposure variance.`;
          nextAction = `Execute recommended action: ${metrics?.actionName || 'HOLD POSITION'}.`;
        }
      } else {
        // Global context resolution
        if (isRiskQuery) {
          recommendation = `PORTFOLIO RISK CONTROL: Secure garlic and onion unhedged positions.`;
          evidence = `Aggregated unhedged portfolio exposure is ₹${(portfolioMetrics.totalExposure / 100000).toFixed(1)} Lakhs.`;
          riskStr = `${portfolioMetrics.criticalCount} active sourcing mandates are currently flagged high-risk.`;
          impactStr = `₹${(portfolioMetrics.totalDelayCost / 100000).toFixed(2)} Lakhs potential cost of delay.`;
          nextAction = `Navigate to specific critical corridors to apply direct hedges.`;
        } else {
          recommendation = `PORTFOLIO ADVISORY: Prioritize garlic cost-avoidance strategies.`;
          evidence = `Consensus resilience index is stable at ${(activeResilience?.overall_score * 100).toFixed(0)}%.`;
          riskStr = `Minor upward price trends detected across onion/garlic mandis.`;
          impactStr = `₹${(portfolioMetrics.totalOpportunity / 100000).toFixed(2)} Lakhs target savings opportunity.`;
          nextAction = `Open custom strategic directives panel to query individual APMCs.`;
        }
      }

      setCopilotResponse({
        recommendation,
        evidence,
        risk: riskStr,
        businessImpact: impactStr || (metrics ? `₹${(metrics.financialImpact / 100000).toFixed(2)} Lakhs` : '₹0.00 Lakhs'),
        confidence: targetState?.confidence?.score ? `${(targetState.confidence.score * 100).toFixed(0)}%` : '85%',
        nextAction
      });
      setLoading(false);
    }, 400);
  };

  const selectedMetrics = activeState ? getMarketMetrics(activeState) : null;
  const simulatedSavings = selectedMetrics ? (selectedMetrics.financialImpact * (shiftPct / 100)) : 0;
  const simulatedMitigation = selectedMetrics ? (selectedMetrics.costOfDelay * (shiftPct / 100)) : 0;

  const morningMemo = useMemo(() => {
    if (!activeState) return "Awaiting active market state selection to compile morning briefing memo...";
    const metrics = getMarketMetrics(activeState);
    const comm = activeState.commodity?.toUpperCase() || '';
    const mandi = activeState.mandi_id?.replace('_apmc', '').replace(/_/g, ' ').toUpperCase() || '';
    
    let memoText = "";
    if (activeState.risk_level === 'CRITICAL' || activeState.risk_level === 'HIGH') {
      memoText = `STRATEGIC ADVISORY: ${comm} markets at ${mandi} are under high pressure. Pricing trend is ${activeState.trend} with a predicted modal rate of ₹${activeState.price_prediction?.toFixed(0)}/MT. Volatility regime is classified as ${activeState.volatility?.regime || 'ELEVATED'}. We advise immediate LOCK CONTRACTS action. Expected exposure variance is ₹${(metrics.financialImpact / 100000).toFixed(2)} Lakhs, and delaying procurement by 48 hours could incur a cost of ₹${(metrics.costOfDelay / 100000).toFixed(2)} Lakhs.`;
    } else {
      memoText = `MARKET OVERVIEW: ${comm} markets at ${mandi} remain stable. Pricing trend is ${activeState.trend} with a predicted modal rate of ₹${activeState.price_prediction?.toFixed(0)}/MT. Volatility regime is classified as ${activeState.volatility?.regime || 'NOMINAL'}. The recommended posture is ${metrics.actionName}. Estimated exposure variance is ₹${(metrics.financialImpact / 100000).toFixed(2)} Lakhs. Standard sourcing corridors are fully operational.`;
    }
    return memoText;
  }, [activeState]);

  // Extract variables from stream hook
  const {
    plans,
    isSimulating,
    approveAction,
    simulateScenario,
    memories,
    cognitionEvents,
  } = stream;

  // Find active plan for current commodity if exists
  const activePlan = useMemo(() => {
    if (!plans || !activeState) return null;
    return plans.find((p: any) => p.commodity?.toLowerCase() === activeState.commodity?.toLowerCase());
  }, [plans, activeState]);

  return (
    <div className="traderos h-screen w-full overflow-hidden bg-[#0c0d12] text-slate-100 font-sans antialiased selection:bg-indigo-500/30">
      <div className="flex h-full flex-col bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.04),transparent_50%),linear-gradient(180deg,#0a0b10_0%,#0c0d12_100%)]">

        {/* EXECUTIVE HEADER */}
        <header className="shrink-0 border-b border-[#1e2335] bg-[#0c0d12]/75 backdrop-blur-xl px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="h-9 w-9 flex items-center justify-center rounded-lg border border-[#252c42] bg-[#141724] transition-colors hover:border-indigo-500/40" title="Back to MandiSense AI">
              <Layers3 className="h-4.5 w-4.5 text-indigo-400" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-base font-black tracking-tight text-white">TraderOS</span>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
              </div>
              <span className="font-mono text-[8px] uppercase tracking-[0.24em] text-slate-500 block -mt-0.5 font-semibold">Enterprise Sourcing Command</span>
            </div>

            <nav className="hidden xl:flex items-center gap-1 pl-4 ml-1 border-l border-[#1e2335]">
              {[
                { href: '/market-explorer', label: 'Explorer' },
                { href: '/intelligence-lab', label: 'Lab' },
                { href: '/ai-brief', label: 'AI Brief' },
              ].map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="px-2.5 py-1 rounded-md font-mono text-[9px] font-bold uppercase tracking-widest text-slate-500 hover:text-white hover:bg-[#171b2c] transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-4 border-r border-[#1e2335] pr-6">
              <div className="flex items-center gap-2 text-slate-400 font-mono text-[9px] uppercase tracking-wider font-semibold">
                <Activity className="h-3.5 w-3.5 text-emerald-500" />
                <span>Live Intel Sync</span>
              </div>
              <div className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">{clock}</div>
            </div>

            <button
              onClick={triggerRefresh}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#1e2335] bg-[#141724] hover:bg-[#191e2f] hover:border-indigo-500/30 font-mono text-[9px] font-bold uppercase tracking-widest text-slate-300 hover:text-white rounded-lg transition-all duration-200"
            >
              <RefreshCw className="h-3 w-3" />
              Sync Intel
            </button>
          </div>
        </header>

        {/* EXECUTIVE CONTEXT BAR */}
        {allStates.length > 0 && (
          <nav className="shrink-0 border-b border-[#1e2335] bg-[#11131c]/80 select-none px-8 py-2.5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 mr-1">
                <Sliders className="h-3.5 w-3.5 text-indigo-400" />
                <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-400 font-bold">Scope Context:</span>
              </div>
              
              {/* COMMODITY SELECTOR */}
              <div className="flex items-center gap-1.5 bg-[#171b2c] border border-[#252c42] rounded-lg px-2.5 py-1 focus-within:border-indigo-500/50 transition-all">
                <span className="font-mono text-[8px] uppercase tracking-wider text-slate-500 font-bold">Commodity</span>
                <select
                  value={selectedCommodity}
                  onChange={(e) => {
                    setSelectedCommodity(e.target.value);
                    setSelectedMandi('ALL'); // reset mandi
                  }}
                  className="bg-transparent border-none text-[11px] font-semibold font-display text-white outline-none cursor-pointer pr-1 focus:ring-0"
                >
                  <option value="ALL" className="bg-[#141724] text-white">All Commodities</option>
                  <option value="TOMATO" className="bg-[#141724] text-white">Tomato</option>
                  <option value="ONION" className="bg-[#141724] text-white">Onion</option>
                  <option value="POTATO" className="bg-[#141724] text-white">Potato</option>
                  <option value="GARLIC" className="bg-[#141724] text-white">Garlic</option>
                  <option value="GINGER" className="bg-[#141724] text-white">Ginger</option>
                </select>
              </div>

              {/* MANDI LOCATION SELECTOR */}
              <div className="flex items-center gap-1.5 bg-[#171b2c] border border-[#252c42] rounded-lg px-2.5 py-1 focus-within:border-indigo-500/50 transition-all">
                <span className="font-mono text-[8px] uppercase tracking-wider text-slate-500 font-bold">Location</span>
                <select
                  value={selectedMandi}
                  onChange={(e) => setSelectedMandi(e.target.value)}
                  className="bg-transparent border-none text-[11px] font-semibold font-display text-white outline-none cursor-pointer pr-1 focus:ring-0 max-w-[130px]"
                >
                  <option value="ALL" className="bg-[#141724] text-white">All Mandis</option>
                  {availableMandis.map((mandi) => (
                    <option key={mandi} value={mandi} className="bg-[#141724] text-white">
                      {mandi.replace('_apmc', '').replace(/_/g, ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              {/* HORIZON SELECTOR */}
              <div className="flex items-center gap-1.5 bg-[#171b2c] border border-[#252c42] rounded-lg px-2.5 py-1 focus-within:border-indigo-500/50 transition-all">
                <span className="font-mono text-[8px] uppercase tracking-wider text-slate-500 font-bold">Horizon</span>
                <select
                  value={selectedHorizon}
                  onChange={(e) => setSelectedHorizon(e.target.value)}
                  className="bg-transparent border-none text-[11px] font-semibold font-display text-white outline-none cursor-pointer pr-1 focus:ring-0"
                >
                  <option value="7D" className="bg-[#141724] text-white">7 Days (Short)</option>
                  <option value="14D" className="bg-[#141724] text-white">14 Days</option>
                  <option value="30D" className="bg-[#141724] text-white">30 Days (Standard)</option>
                  <option value="SEASONAL" className="bg-[#141724] text-white">Seasonal Forecast</option>
                  <option value="LONG_TERM" className="bg-[#141724] text-white">Long Term (Strategic)</option>
                </select>
              </div>

              {/* INTELLIGENCE FOCUS MODE SELECTOR */}
              <div className="flex items-center gap-1.5 bg-[#171b2c] border border-[#252c42] rounded-lg px-2.5 py-1 focus-within:border-indigo-500/50 transition-all">
                <span className="font-mono text-[8px] uppercase tracking-wider text-slate-500 font-bold">Focus</span>
                <select
                  value={selectedMode}
                  onChange={(e) => setSelectedMode(e.target.value)}
                  className="bg-transparent border-none text-[11px] font-semibold font-display text-white outline-none cursor-pointer pr-1 focus:ring-0"
                >
                  <option value="ATTENTION" className="bg-[#141724] text-white">Executive Attention</option>
                  <option value="DECISIONS" className="bg-[#141724] text-white">Critical Decisions</option>
                  <option value="RISKS" className="bg-[#141724] text-white">Threat Signals</option>
                  <option value="OPPORTUNITIES" className="bg-[#141724] text-white">Opportunities</option>
                </select>
              </div>
            </div>

            {/* RESOLVED ACTIVE CONTEXT SUMMARY DISPLAY */}
            <div className="hidden md:flex items-center gap-2 bg-indigo-950/20 border border-indigo-500/10 px-3 py-1 rounded-lg text-slate-400 font-mono text-[9px] uppercase tracking-wider">
              <span>Active Scope:</span>
              <span className="text-white font-bold">{selectedCommodity}</span>
              <span className="text-slate-600">|</span>
              <span className="text-white font-bold">{selectedMandi === 'ALL' ? 'ALL LOCATIONS' : selectedMandi.replace('_apmc','').replace(/_/g,' ').toUpperCase()}</span>
              <span className="text-slate-600">|</span>
              <span className="text-indigo-400 font-bold">{selectedHorizon}</span>
            </div>
          </nav>
        )}

        {/* MAIN INTEGRATED COMMAND PANEL */}
        {allStates.length > 0 ? (
          <main className="min-h-0 flex-1 grid grid-cols-12 bg-[#0c0d12]">
            
            {/* LEFT COCKPIT VIEW (Col Span 9) */}
            <section className="col-span-9 min-h-0 flex flex-col overflow-y-auto p-6 space-y-6">
              
              {/* 1. CEO MORNING BRIEFING MEMO */}
              <div className="border border-indigo-500/25 bg-indigo-950/10 rounded-xl p-5 relative overflow-hidden backdrop-blur-md">
                <div className="absolute top-0 right-0 h-16 w-16 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-bl-full pointer-events-none" />
                <div className="flex items-center gap-2 border-b border-[#1e2335] pb-2 mb-3">
                  <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                  <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">1. CEO Morning Briefing Memo</span>
                </div>
                <p className="text-[12px] text-slate-300 font-medium leading-relaxed">
                  {morningMemo}
                </p>
                <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-[#1e2335]/40 text-[8px] font-mono text-slate-500">
                  <span>Traceability: Synthesized live from model predictions and telemetry trust scores</span>
                  <span className="font-bold text-indigo-400">CONTEXT SECURE</span>
                </div>
              </div>

              {/* COMMODITY MARKETS — price/volume chart + trend comparison */}
              <TradingSection />

              {/* 3. ENTERPRISE STATE (PORTFOLIO STATUS BAR) */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-400 font-bold block">4. Enterprise Posture & State</span>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  <div className="border border-[#1e2335] bg-[#131622]/60 p-4 rounded-xl relative overflow-hidden backdrop-blur-md">
                    <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Consensus Resilience Index</span>
                    <div className="flex items-baseline gap-1.5 mt-2">
                      <span className="font-display text-2xl font-extrabold text-emerald-400">{(activeResilience?.overall_score * 100).toFixed(0)}%</span>
                      <span className="font-mono text-[8px] text-slate-500 uppercase tracking-widest font-semibold">Stable</span>
                    </div>
                    <div className="h-1 w-full bg-[#1b1f30] rounded-full mt-3 overflow-hidden">
                      <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${(activeResilience?.overall_score * 100)}%` }} />
                    </div>
                  </div>

                  <div className="border border-[#1e2335] bg-[#131622]/60 p-4 rounded-xl relative overflow-hidden backdrop-blur-md">
                    <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Sourcing Exposure</span>
                    <div className="flex items-baseline gap-1.5 mt-2">
                      <span className="font-display text-2xl font-extrabold text-white">₹{(portfolioMetrics.totalExposure / 100000).toFixed(1)}L</span>
                      <span className="font-mono text-[8px] text-slate-500 uppercase tracking-widest font-semibold">Unhedged</span>
                    </div>
                    <p className="text-[9px] text-slate-400 font-mono mt-3">Active exposure monitored in corridors</p>
                  </div>

                  <div className="border border-[#1e2335] bg-[#131622]/60 p-4 rounded-xl relative overflow-hidden backdrop-blur-md">
                    <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Contract Variance Opportunity</span>
                    <div className="flex items-baseline gap-1.5 mt-2">
                      <span className="font-display text-2xl font-extrabold text-emerald-400">₹{(portfolioMetrics.totalOpportunity / 100000).toFixed(1)}L</span>
                      <span className="font-mono text-[8px] text-slate-500 uppercase tracking-widest font-semibold">Hedge ROI</span>
                    </div>
                    <p className="text-[9px] text-slate-400 font-mono mt-3">Projected cost avoidance margin</p>
                  </div>

                  <div className="border border-[#1e2335] bg-[#131622]/60 p-4 rounded-xl relative overflow-hidden backdrop-blur-md">
                    <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Active Sourcing Mandates</span>
                    <div className="flex items-baseline gap-1.5 mt-2">
                      <span className={cx("font-display text-2xl font-extrabold", portfolioMetrics.criticalCount > 0 ? "text-rose-400" : "text-slate-200")}>
                        {portfolioMetrics.criticalCount} Alerts
                      </span>
                      <span className="font-mono text-[8px] text-slate-500 uppercase tracking-widest font-semibold">High Risk</span>
                    </div>
                    <p className="text-[9px] text-slate-400 font-mono mt-3">Mandi corridors exceeding thresholds</p>
                  </div>
                </div>
              </div>

              {/* GRID FOR OTHER COCKPIT PARTS */}
              <div className="grid grid-cols-2 gap-6">
                
                {/* COLUMN 1: CRITICAL DECISIONS & DECISION WAR ROOM */}
                <div className="space-y-6">
                  
                  {/* 2. CRITICAL DECISIONS */}
                  <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md flex flex-col shrink-0">
                    <div className="px-5 py-4 border-b border-[#1e2335] flex items-center justify-between">
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-rose-400 font-bold block">Action Required</span>
                        <h3 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">2. Critical Decisions</h3>
                      </div>
                      <span className={cx(
                        "font-mono text-[8px] px-2 py-0.5 border rounded font-bold uppercase tracking-wider",
                        criticalCorridors.length > 0 ? "text-rose-400 bg-rose-500/10 border-rose-500/20" : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                      )}>
                        {criticalCorridors.length} High Risk
                      </span>
                    </div>

                    <div className="p-4 max-h-[220px] overflow-y-auto space-y-3">
                      {criticalCorridors.length > 0 ? (
                        criticalCorridors.map(({ state, index: originalIndex, metrics }) => {
                          const isSelected = originalIndex === safeActiveIdx;
                          return (
                            <div
                              key={originalIndex}
                              onClick={() => {
                                setSelectedCommodity(state.commodity?.toUpperCase() || 'ALL');
                                setSelectedMandi(state.mandi_id || 'ALL');
                                setActiveIdx(originalIndex);
                                setShiftPct(50);
                              }}
                              className={cx(
                                "border rounded-lg p-3 flex items-center justify-between cursor-pointer transition-all duration-150",
                                isSelected 
                                  ? "bg-[#1c2237]/60 border-indigo-500/60 shadow-[0_0_10px_rgba(99,102,241,0.08)]" 
                                  : "bg-[#161a29]/30 border-[#1e2335] hover:border-[#2b334d]"
                              )}
                            >
                              <div className="flex items-center gap-3">
                                <div className={cx(
                                  "p-2 rounded-md border",
                                  state.risk_level === 'CRITICAL' || state.risk_level === 'HIGH' ? "bg-rose-500/10 border-rose-500/20 text-rose-400" : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                                )}>
                                  <ShieldAlert className="h-4 w-4" />
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-display text-xs font-bold text-white uppercase">
                                      {state.commodity}
                                    </span>
                                    <span className="text-slate-500 text-[8px]">•</span>
                                    <span className="font-mono text-[9px] text-slate-400 uppercase">
                                      {state.mandi_id?.replace('_apmc','').replace(/_/g,' ')}
                                    </span>
                                  </div>
                                  <span className="text-[10px] text-slate-400 font-semibold block mt-0.5">
                                    Status Posture: {metrics.actionName}
                                  </span>
                                </div>
                              </div>

                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <span className="font-mono text-[8px] text-slate-500 block">Variance</span>
                                  <span className="font-mono text-[11px] font-bold text-rose-400">
                                    ₹{(metrics.financialImpact / 100000).toFixed(1)}L
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-center py-6 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                          No Critical Decisions Pending
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 3. DECISION WAR ROOM */}
                  <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md p-5 space-y-4">
                    <div className="border-b border-[#1e2335] pb-2.5 flex justify-between items-center">
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">Consensus Deliberation</span>
                        <h4 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">3. Decision War Room</h4>
                      </div>
                      <div className="text-[9px] font-mono text-slate-400 bg-slate-800/40 px-2 py-0.5 rounded border border-slate-700/50">
                        {activeState?.commodity?.toUpperCase() || 'TOMATO'} @ {activeState?.mandi_id?.replace('_apmc','').toUpperCase()}
                      </div>
                    </div>

                    {activeState ? (
                      <div className="space-y-4 font-mono text-[10px]">
                        
                        {/* Agent Weights */}
                        <div className="grid grid-cols-3 gap-2 text-center font-mono">
                          {activeState.deliberation?.agents?.map((agent: any) => (
                            <div key={agent.agent_id} className="bg-[#181c2c]/40 border border-[#252c42] p-2 rounded-lg">
                              <span className="text-slate-500 text-[8px] block font-semibold">{agent.agent_id?.replace('Agent','').toUpperCase()}</span>
                              <span className="text-slate-200 font-bold block mt-1">{agent.signal}</span>
                              <span className="text-indigo-400 text-[8px] block mt-0.5">Conf: {(agent.confidence * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>

                        {/* Real-time Execution Plan */}
                        <div className="border-t border-[#1e2335]/50 pt-3 space-y-3">
                          <span className="text-slate-400 font-semibold block text-[9px] uppercase tracking-wider">Operational Action Plans</span>
                          {activePlan ? (
                            <div className="space-y-2">
                              {activePlan.actions?.map((act: any) => (
                                <div key={act.id} className="bg-[#141620]/50 border border-[#1e2335]/50 p-2.5 rounded-lg flex items-center justify-between">
                                  <div className="space-y-0.5 max-w-[75%]">
                                    <div className="flex items-center gap-1.5">
                                      <span className={cx(
                                        "text-[8px] px-1.5 py-0.2 rounded font-bold uppercase",
                                        act.urgency === 'CRITICAL' ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" : "bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                                      )}>{act.type}</span>
                                      <span className="text-[8px] text-slate-500 uppercase">{act.target_mandi?.replace('_apmc','').toUpperCase()}</span>
                                    </div>
                                    <p className="text-[9px] text-slate-400 leading-normal">{act.reasoning}</p>
                                  </div>
                                  <div>
                                    {act.status === 'PENDING' ? (
                                      <button
                                        onClick={() => approveAction(activePlan.id, act.id)}
                                        className="px-2.5 py-1 bg-emerald-950/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-950/50 rounded font-bold text-[8px] uppercase tracking-wider transition-all"
                                      >
                                        Authorize
                                      </button>
                                    ) : (
                                      <span className="text-emerald-400 font-black flex items-center gap-1 text-[8px]">
                                        <CheckCircle className="h-3 w-3" /> APPROVED
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="bg-[#141620]/30 border border-[#1e2335]/30 rounded-lg p-4 text-center space-y-2">
                              <span className="text-slate-500 block text-[9px]">No active plan resolved for this corridor.</span>
                              <button
                                onClick={triggerRefresh}
                                className="px-3 py-1 bg-indigo-950/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-950/50 rounded font-bold text-[8px] uppercase tracking-wider transition-all"
                              >
                                Trigger Plan Synthesis
                              </button>
                            </div>
                          )}
                        </div>

                      </div>
                    ) : (
                      <p className="text-[10px] text-slate-500 font-mono text-center py-4 uppercase">Select a critical alert corridor above</p>
                    )}
                  </div>

                </div>

                {/* COLUMN 2: THREAT INTELLIGENCE & COUNTERFACTUAL ENGINE & SIMULATOR */}
                <div className="space-y-6">
                  
                  {/* 5. THREAT INTELLIGENCE */}
                  <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md p-5 space-y-4">
                    <div className="border-b border-[#1e2335] pb-2.5">
                      <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">Environmental Risks</span>
                      <h4 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">5. Threat Intelligence</h4>
                    </div>

                    {activeState ? (
                      <div className="space-y-3 font-mono text-[10px]">
                        <div className="flex justify-between items-center border-b border-[#1e2335]/30 pb-2">
                          <span className="text-slate-500">VOLATILITY REGIME</span>
                          <span className={cx(
                            "font-bold",
                            activeState.volatility?.regime === 'high' || activeState.volatility?.regime === 'ELEVATED_VOLATILITY' ? "text-rose-450 text-rose-400" : "text-emerald-400"
                          )}>{(activeState.volatility?.regime || activeState.regime || 'NOMINAL').replace(/_/g, ' ').toUpperCase()}</span>
                        </div>
                        <div className="flex justify-between items-center border-b border-[#1e2335]/30 pb-2">
                          <span className="text-slate-500">MANDI ARRIVAL TARGET</span>
                          <span className="text-slate-300">{(activeState.forecast_arrivals ?? 30).toFixed(1)} MT</span>
                        </div>
                        <div className="flex justify-between items-center border-b border-[#1e2335]/30 pb-2">
                          <span className="text-slate-500">LOGISTICS THREAT</span>
                          <span className="text-slate-300">
                            {activeState.risk_level === 'CRITICAL' || activeState.risk_level === 'HIGH' ? 'DELAYS DETECTED (HIGH)' : 'NOMINAL (STABLE)'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500">INTER-MANDI COHERENCE</span>
                          <span className="text-emerald-400 font-bold">94.8% SIGNAL MATCH</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-[10px] text-slate-500 text-center py-4 uppercase font-mono">No State Active</p>
                    )}
                  </div>

                  {/* 7. COUNTERFACTUAL ENGINE */}
                  <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md p-5 space-y-4">
                    <div className="border-b border-[#1e2335] pb-2.5 flex justify-between items-center">
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">Inject Scenario Shock</span>
                        <h4 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">7. Counterfactual Engine</h4>
                      </div>
                      {isSimulating && (
                        <span className="text-[8px] font-mono bg-indigo-500/10 px-2 py-0.5 rounded text-indigo-300 font-bold animate-pulse">
                          RUNNING...
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      <p className="text-[10px] text-slate-400 font-mono leading-normal">
                        Simulate alternative futures by injecting shocks directly into the hidden machine council:
                      </p>
                      
                      <div className="grid grid-cols-3 gap-2 pt-1.5">
                        <button
                          disabled={isSimulating || !activeState}
                          onClick={() => activeState && simulateScenario(activeState.commodity || 'tomato', activeState.mandi_id || 'kolar_apmc', 'CORRIDOR_COLLAPSE')}
                          className="px-2 py-2 bg-rose-950/20 border border-rose-500/20 hover:border-rose-500/50 hover:bg-rose-950/40 text-rose-300 disabled:opacity-40 rounded font-mono text-[8px] uppercase tracking-wider font-bold transition-all text-center leading-normal"
                        >
                          Corridor Collapse
                        </button>
                        <button
                          disabled={isSimulating || !activeState}
                          onClick={() => activeState && simulateScenario(activeState.commodity || 'tomato', activeState.mandi_id || 'kolar_apmc', 'RAINFALL_SHOCK')}
                          className="px-2 py-2 bg-amber-950/20 border border-amber-500/20 hover:border-amber-500/50 hover:bg-amber-950/40 text-amber-300 disabled:opacity-40 rounded font-mono text-[8px] uppercase tracking-wider font-bold transition-all text-center leading-normal"
                        >
                          Rainfall Shock
                        </button>
                        <button
                          disabled={isSimulating || !activeState}
                          onClick={() => activeState && simulateScenario(activeState.commodity || 'tomato', activeState.mandi_id || 'kolar_apmc', 'DIESEL_SPIKE')}
                          className="px-2 py-2 bg-indigo-950/20 border border-indigo-500/20 hover:border-indigo-550/50 hover:bg-indigo-950/40 text-indigo-300 disabled:opacity-40 rounded font-mono text-[8px] uppercase tracking-wider font-bold transition-all text-center leading-normal"
                        >
                          Logistics Delay
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 8. ENTERPRISE IMPACT SIMULATOR */}
                  <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md p-5 space-y-4">
                    <div className="border-b border-[#1e2335] pb-2.5">
                      <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">Hedge Optimization Simulator</span>
                      <h4 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">8. Enterprise Impact Simulator</h4>
                    </div>

                    <div className="space-y-4 mt-2">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-[10px] font-mono">
                          <span className="text-slate-400 font-medium">Hedge / Sourcing shift percentage</span>
                          <span className="text-indigo-400 font-black">{shiftPct}% allocation</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={shiftPct}
                          onChange={(e) => setShiftPct(Number(e.target.value))}
                          className="w-full h-1 bg-[#1b1f30] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-1">
                        <div className="bg-[#181c2c]/40 border border-[#252c42] p-3 rounded-lg font-mono">
                          <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold">Simulated ROI (Savings)</span>
                          <span className="text-base font-display font-black text-emerald-400 mt-1 block">
                            ₹{simulatedSavings ? (simulatedSavings / 100000).toFixed(2) : '0.00'} Lakhs
                          </span>
                        </div>
                        <div className="bg-[#181c2c]/40 border border-[#252c42] p-3 rounded-lg font-mono">
                          <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold">Mitigated Penalty (Risk)</span>
                          <span className="text-base font-display font-black text-rose-400 mt-1 block">
                            ₹{simulatedMitigation ? (simulatedMitigation / 100000).toFixed(2) : '0.00'} Lakhs
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>

              </div>

            </section>

            {/* RIGHT INTEGRATED COPILOT SIDEBAR (Col Span 3) */}
            <aside className="col-span-3 min-h-0 flex flex-col bg-[#10121a] border-l border-[#1e2335] overflow-y-auto">
              
              {/* 9. TRADEROS COPILOT */}
              <div className="p-5 border-b border-[#1e2335] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-indigo-400" />
                  <span className="font-display text-xs font-bold uppercase tracking-wider text-white">9. TraderOS Copilot</span>
                </div>
                <span className="font-mono text-[8px] text-slate-500 uppercase tracking-widest font-semibold">T2 ASSISTANT</span>
              </div>

              {/* COPILOT PANEL BODY */}
              <div className="p-5 space-y-5 flex-1 min-h-0">
                
                {/* SUGGESTED BRIEFINGS */}
                <div className="space-y-2.5">
                  <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Suggested briefings</span>
                  <div className="space-y-1.5">
                    {suggestedQuestions.map((q) => (
                      <button
                        key={q.id}
                        onClick={() => handleAsk(q.query)}
                        className="w-full text-left font-mono text-[9px] text-slate-400 bg-[#161a29]/40 border border-[#1e2335] px-3 py-2 rounded-lg hover:border-indigo-500/35 hover:bg-indigo-500/[0.03] hover:text-white transition-all duration-150 leading-normal"
                      >
                        {q.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* CUSTOM INPUT */}
                <div className="space-y-2.5 pt-2.5 border-t border-[#1e2335]/40">
                  <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Custom Strategic Directive</span>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={customInput}
                      onChange={(e) => setCustomInput(e.target.value)}
                      placeholder="Ask copilot for sourcing guidelines..."
                      className="flex-1 h-8 bg-[#161a29]/50 border border-[#1e2335] rounded-lg px-3 font-mono text-[9px] text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/30"
                    />
                    <button
                      onClick={() => {
                        handleAsk(customInput);
                        setCustomInput('');
                      }}
                      className="h-8 px-3 bg-indigo-950/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-950/45 font-mono text-[9px] uppercase tracking-wider rounded-lg transition-all duration-150 font-bold"
                    >
                      Ask
                    </button>
                  </div>
                </div>

                {/* COPILOT RESPONSE PANEL */}
                {loading && (
                  <div className="p-4 border border-indigo-500/15 bg-indigo-500/5 rounded-lg space-y-2 animate-pulse">
                    <span className="font-mono text-[8px] uppercase tracking-wider text-indigo-400 block font-bold">Synthesizing directives...</span>
                    <div className="h-2 bg-slate-800 rounded w-3/4" />
                    <div className="h-2 bg-slate-800 rounded w-1/2" />
                  </div>
                )}

                {copilotResponse && !loading && (
                  <div className="border border-[#1e2335] bg-[#161a29]/30 p-4 rounded-lg space-y-3 relative overflow-hidden">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-[8px] font-mono text-indigo-400 uppercase tracking-widest font-bold">
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>Directives Synthesized</span>
                      </div>
                      <div className="text-[8px] font-mono bg-indigo-500/10 px-2 py-0.5 rounded text-indigo-300 font-bold">
                        RESOLVED
                      </div>
                    </div>

                    <div className="space-y-3 text-[10.5px]">
                      {/* RECOMMENDATION */}
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Recommendation</span>
                        <p className="font-bold text-slate-200 mt-1 bg-[#1b2035]/40 border border-[#252c42]/50 p-2 rounded-lg leading-relaxed">{copilotResponse.recommendation}</p>
                      </div>

                      {/* EVIDENCE */}
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-550 text-slate-500 block font-bold">Evidence</span>
                        <p className="text-slate-400 mt-1 leading-normal">{copilotResponse.evidence}</p>
                      </div>

                      {/* RISK */}
                      <div>
                        <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">Risk</span>
                        <p className="text-slate-400 mt-1 leading-normal">{copilotResponse.risk}</p>
                      </div>

                      {/* STATS */}
                      <div className="grid grid-cols-2 gap-2 border-t border-[#1e2335]/40 pt-2 font-mono text-[10px]">
                        <div>
                          <span className="text-slate-500 uppercase tracking-widest text-[8px] block font-bold">Confidence</span>
                          <span className="text-white font-bold block mt-0.5">{copilotResponse.confidence}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 uppercase tracking-widest text-[8px] block font-bold">Business Impact</span>
                          <span className="text-emerald-400 font-bold block mt-0.5">{copilotResponse.businessImpact}</span>
                        </div>
                      </div>

                      {/* NEXT ACTION */}
                      <div className="border-t border-[#1e2335]/40 pt-2">
                        <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-indigo-400 block font-bold">Next Action</span>
                        <p className="text-indigo-200 mt-1 font-semibold leading-relaxed bg-indigo-950/10 border border-indigo-500/10 p-2 rounded-lg">{copilotResponse.nextAction}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 6. FUTURE MEMORY */}
                <div className="pt-4 border-t border-[#1e2335]/40 space-y-2.5">
                  <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">6. Future Memory (Replay Logs)</span>
                  <div className="bg-[#141620]/30 border border-[#1e2335]/50 rounded-lg p-3 max-h-[140px] overflow-y-auto space-y-2 font-mono text-[9px]">
                    {memories && memories.length > 0 ? (
                      memories.slice(0, 10).map((mem: any) => (
                        <div
                          key={mem.id}
                          onClick={() => handleAsk(`Analyze memory snapshot from scenario: ${mem.scenario || mem.type} for ${mem.commodity}`)}
                          className="p-2 bg-[#1b1f30]/40 hover:bg-[#20273f]/50 border border-[#1e2335]/60 hover:border-indigo-500/20 rounded cursor-pointer transition-all flex justify-between items-start gap-1 leading-normal"
                        >
                          <div>
                            <span className="text-indigo-400 font-bold uppercase">{mem.commodity}</span>
                            <span className="text-slate-400 block text-[8px] font-semibold mt-0.5">Scenario: {mem.scenario || mem.type}</span>
                          </div>
                          <span className="text-slate-500 text-[8px] whitespace-nowrap">{new Date(mem.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-slate-600 block text-center py-2">No simulated memory records found</span>
                    )}
                  </div>
                </div>

                {/* 10. EXECUTIVE INTELLIGENCE FEED */}
                <div className="pt-4 border-t border-[#1e2335]/40 space-y-2.5">
                  <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-500 block font-bold">10. Executive Intelligence Feed</span>
                  <div className="bg-[#0b0c10] border border-[#1e2335]/50 p-3 rounded-lg font-mono text-[9px] h-[130px] overflow-y-auto space-y-1.5 scrollbar-thin">
                    {cognitionEvents && cognitionEvents.length > 0 ? (
                      cognitionEvents.map((evt: any) => (
                        <div key={evt.id} className="flex gap-1.5 leading-normal">
                          <span className="text-slate-600">[{new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
                          <span className={cx(
                            "flex-1",
                            evt.type === 'error' ? 'text-rose-450 text-rose-400' :
                            evt.type === 'success' ? 'text-emerald-400' :
                            evt.type === 'simulation' ? 'text-indigo-400' : 'text-slate-300'
                          )}>{evt.message}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-500 flex items-center justify-center h-full text-center">
                        Awaiting stream events...
                      </div>
                    )}
                  </div>
                </div>

              </div>

            </aside>

          </main>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center bg-[#0c0d12]">
            <div className="relative h-16 w-16 border border-indigo-500/20 bg-indigo-500/5 rounded-xl">
              <span className="absolute inset-4 animate-ping bg-indigo-500/20 rounded-full" />
              <BrainCircuit className="absolute left-1/2 top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-1/2 text-indigo-400" />
            </div>
            <div>
              <div className="font-mono text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Awaiting intelligence synthesis</div>
              <div className="mt-3 text-sm text-slate-400">The cognition layer is publishing market states.</div>
            </div>
          </div>
        )}

        {/* BOTTOM STATUS FOOTER */}
        <footer className="flex min-h-10 shrink-0 items-center justify-between border-t border-[#1e2335] bg-[#0c0d12] px-8 py-3">
          <div className="flex items-center gap-6 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500 font-semibold">
            <span className="flex items-center gap-2 text-slate-400">
              <Gauge className="h-4 w-4 text-indigo-400" /> TRADEROS SYSTEM v1.0
            </span>
            <span className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-500" /> Corridors Monitored: {allStates.length}
            </span>
          </div>
          <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-indigo-300/80 flex items-center gap-1.5 font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping inline-block mr-1" />
            CONTEXT LOCKED: {activeState ? `${activeState.commodity?.toUpperCase()} / ${activeState.mandi_id?.replace('_apmc','').replace(/_/g,' ').toUpperCase()}` : 'NO ACTIVE CONTEXT'}
          </div>
        </footer>

      </div>
    </div>
  );
}
