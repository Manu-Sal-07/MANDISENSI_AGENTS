'use client';

import React from 'react';
import { JourneyState, AgentId } from './hooks/useDecisionJourney';
import { Calendar, AlertTriangle, Globe, Layers, CheckCircle } from 'lucide-react';

interface AgentActivationPanelProps {
  currentState: JourneyState;
  onSelectAgent?: (agentId: AgentId) => void;
}

export default function AgentActivationPanel({ currentState, onSelectAgent }: AgentActivationPanelProps) {
  // Helper to determine agent states
  const getAgentStatus = (agent: 'seasonality' | 'arrival' | 'external' | 'ensemble') => {
    const stateOrder: JourneyState[] = [
      'IDLE',
      'OFFLINE_FACTORY',
      'MODEL_REGISTRY',
      'LIVE_INGESTION',
      'LOCATION_INTELLIGENCE',
      'DATA_PROCESSING',
      'DIGITAL_TWIN',
      'SEASONALITY_ANALYSIS',
      'ARRIVAL_ANALYSIS',
      'EXTERNAL_ANALYSIS',
      'META_ENSEMBLE',
      'DECISION_ENGINE',
      'INFRA_DISCOVERY',
      'FINAL_RECOMMENDATION',
      'COMPLETE',
    ];

    const currentIdx = stateOrder.indexOf(currentState);
    
    if (agent === 'seasonality') {
      const activeIdx = stateOrder.indexOf('SEASONALITY_ANALYSIS');
      if (currentIdx === activeIdx) return 'active';
      if (currentIdx > activeIdx) return 'completed';
      return 'idle';
    }
    
    if (agent === 'arrival') {
      const activeIdx = stateOrder.indexOf('ARRIVAL_ANALYSIS');
      if (currentIdx === activeIdx) return 'active';
      if (currentIdx > activeIdx) return 'completed';
      return 'idle';
    }
    
    if (agent === 'external') {
      const activeIdx = stateOrder.indexOf('EXTERNAL_ANALYSIS');
      if (currentIdx === activeIdx) return 'active';
      if (currentIdx > activeIdx) return 'completed';
      return 'idle';
    }
    
    // ensemble
    const activeIdx = stateOrder.indexOf('META_ENSEMBLE');
    if (currentIdx === activeIdx) return 'active';
    if (currentIdx > activeIdx) return 'completed';
    return 'idle';
  };

  const seasonalityStatus = getAgentStatus('seasonality');
  const arrivalStatus = getAgentStatus('arrival');
  const externalStatus = getAgentStatus('external');
  const ensembleStatus = getAgentStatus('ensemble');

  const getStatusClasses = (status: 'idle' | 'active' | 'completed') => {
    switch (status) {
      case 'active':
        return {
          border: 'border-emerald-500 bg-emerald-950/20 shadow-[0_0_20px_rgba(16,185,129,0.15)] scale-[1.01] duration-300',
          text: 'text-emerald-400',
          dot: 'bg-emerald-400 animate-pulse shadow-[0_0_8px_#34d399]',
          badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        };
      case 'completed':
        return {
          border: 'border-slate-800 bg-slate-950/40 opacity-90 hover:border-indigo-500/40 hover:bg-slate-950/60 hover:shadow-[0_0_15px_rgba(99,102,241,0.1)]',
          text: 'text-slate-300',
          dot: 'bg-slate-500',
          badge: 'bg-slate-950/60 text-emerald-400 border-emerald-500/20',
        };
      default:
        return {
          border: 'border-slate-900 bg-slate-950/10 opacity-30 pointer-events-none scale-100',
          text: 'text-slate-600',
          dot: 'bg-slate-800',
          badge: 'bg-slate-950/20 text-slate-600 border-slate-900/30',
        };
    }
  };

  const sTheme = getStatusClasses(seasonalityStatus);
  const aTheme = getStatusClasses(arrivalStatus);
  const eTheme = getStatusClasses(externalStatus);
  const mTheme = getStatusClasses(ensembleStatus);

  // Click handler wrapper
  const handleAgentClick = (agentId: AgentId, status: 'idle' | 'active' | 'completed') => {
    if (status !== 'idle' && onSelectAgent) {
      onSelectAgent(agentId);
    }
  };

  return (
    <div className="w-full bg-[#09101d]/90 backdrop-blur-xl border border-slate-900/80 rounded-[2rem] p-6 md:p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative overflow-hidden">
      {/* Decorative background accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full blur-[120px] pointer-events-none opacity-20 bg-indigo-500/10" />

      {/* Header telemetry area */}
      <div className="relative z-10 border-b border-slate-900 pb-5 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1 text-[9px] font-mono font-bold tracking-[0.2em] text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20 uppercase">
              <Layers className="w-3.5 h-3.5" />
              Agent Core Registry
            </span>
          </div>
          <h3 className="text-lg font-black text-slate-100 tracking-tight">
            Multi-Agent Reasoning & Fusion
          </h3>
          <p className="text-xs text-slate-450 leading-none mt-1 font-sans">
            Click any active/decided agent card to inspect its sub-models and inputs.
          </p>
        </div>
        <div className="text-[10px] font-mono text-slate-500">
          VOTING_SCHEME: STATIC_CONFIDENCE_FUSION
        </div>
      </div>

      {/* Main Grid */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Left Column: 3 Agents (6 Cols) */}
        <div className="lg:col-span-6 space-y-4">
          
          {/* Agent 1: Seasonality Agent */}
          <div 
            onClick={() => handleAgentClick('seasonality', seasonalityStatus)}
            className={`border rounded-2xl p-4 transition-all duration-300 ${sTheme.border} ${
              seasonalityStatus !== 'idle' ? 'cursor-pointer hover:scale-[1.01]' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-2 rounded-xl bg-slate-900/80 border border-slate-800 ${sTheme.text}`}>
                  <Calendar className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h4 className="text-xs font-black text-slate-100 tracking-tight">Seasonality Agent</h4>
                  <span className="text-[9px] font-mono text-slate-500">9 Models Activated</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {seasonalityStatus === 'completed' && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
                <span className={`text-[9px] font-mono uppercase px-2 py-0.5 border rounded ${sTheme.badge}`}>
                  {seasonalityStatus === 'active' ? 'PROCESSING' : seasonalityStatus === 'completed' ? 'DECIDED' : 'PENDING'}
                </span>
              </div>
            </div>

            {seasonalityStatus !== 'idle' && (
              <div className="space-y-2 text-[11px] font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Cycle Trend Index:</span>
                  <span className="text-emerald-400 font-bold">92% Match</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Combined Vote:</span>
                  <span className="text-emerald-400 font-bold">BULLISH (HOLD)</span>
                </div>
                {/* Micro contribution bar */}
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className="bg-emerald-500 h-full rounded-full transition-all duration-1000" style={{ width: '35%' }} />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 pt-0.5">
                  <span>Ensemble Weight</span>
                  <span>0.35</span>
                </div>
              </div>
            )}
          </div>

          {/* Agent 2: Arrival Agent */}
          <div 
            onClick={() => handleAgentClick('arrival', arrivalStatus)}
            className={`border rounded-2xl p-4 transition-all duration-300 ${aTheme.border} ${
              arrivalStatus !== 'idle' ? 'cursor-pointer hover:scale-[1.01]' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-2 rounded-xl bg-slate-900/80 border border-slate-800 ${aTheme.text}`}>
                  <AlertTriangle className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h4 className="text-xs font-black text-slate-100 tracking-tight">Arrival Agent</h4>
                  <span className="text-[9px] font-mono text-slate-500">8 Models Activated</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {arrivalStatus === 'completed' && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
                <span className={`text-[9px] font-mono uppercase px-2 py-0.5 border rounded ${aTheme.badge}`}>
                  {arrivalStatus === 'active' ? 'PROCESSING' : arrivalStatus === 'completed' ? 'DECIDED' : 'PENDING'}
                </span>
              </div>
            </div>

            {arrivalStatus !== 'idle' && (
              <div className="space-y-2 text-[11px] font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Supply Stress Index:</span>
                  <span className="text-emerald-400 font-bold">89% Match</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Combined Vote:</span>
                  <span className="text-emerald-400 font-bold">HOLD (Supply Gap)</span>
                </div>
                {/* Micro contribution bar */}
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className="bg-emerald-500 h-full rounded-full transition-all duration-1000" style={{ width: '40%' }} />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 pt-0.5">
                  <span>Ensemble Weight</span>
                  <span>0.40</span>
                </div>
              </div>
            )}
          </div>

          {/* Agent 3: External Factors Agent */}
          <div 
            onClick={() => handleAgentClick('external', externalStatus)}
            className={`border rounded-2xl p-4 transition-all duration-300 ${eTheme.border} ${
              externalStatus !== 'idle' ? 'cursor-pointer hover:scale-[1.01]' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-2 rounded-xl bg-slate-900/80 border border-slate-800 ${eTheme.text}`}>
                  <Globe className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h4 className="text-xs font-black text-slate-100 tracking-tight">External Factors Agent</h4>
                  <span className="text-[9px] font-mono text-slate-500">6 Models Activated</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {externalStatus === 'completed' && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
                <span className={`text-[9px] font-mono uppercase px-2 py-0.5 border rounded ${eTheme.badge}`}>
                  {externalStatus === 'active' ? 'PROCESSING' : externalStatus === 'completed' ? 'DECIDED' : 'PENDING'}
                </span>
              </div>
            </div>

            {externalStatus !== 'idle' && (
              <div className="space-y-2 text-[11px] font-mono">
                <div className="flex justify-between text-slate-400">
                  <span>Macro Impact Index:</span>
                  <span className="text-emerald-400 font-bold">81% Match</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Combined Vote:</span>
                  <span className="text-emerald-400 font-bold">HOLD (Govt Support)</span>
                </div>
                {/* Micro contribution bar */}
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className="bg-emerald-500 h-full rounded-full transition-all duration-1000" style={{ width: '25%' }} />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 pt-0.5">
                  <span>Ensemble Weight</span>
                  <span>0.25</span>
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Right Column: Dynamic Fusion Schematic (6 Cols) */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center border border-slate-900 bg-slate-950/40 rounded-3xl p-6 relative overflow-hidden min-h-[350px]">
          
          {/* Ambient center background radial gradient */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.06),transparent_70%)]" />

          {/* Glowing Fusion SVG Schematic */}
          <div className="relative z-10 w-full flex flex-col items-center gap-8">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block text-center">
              Active Fusion Topology
            </span>

            {/* Fused Network Drawing */}
            <div className="relative w-64 h-36 flex items-center justify-between">
              
              {/* Agent Nodes Left */}
              <div className="flex flex-col justify-between h-full z-10">
                {/* Seasonality Dot */}
                <div 
                  onClick={() => handleAgentClick('seasonality', seasonalityStatus)}
                  className={`w-8 h-8 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-[10px] font-mono transition-all duration-300 ${
                    seasonalityStatus !== 'idle' ? 'border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.3)] text-emerald-400 cursor-pointer hover:border-indigo-500/80 hover:text-white' : 'text-slate-600'
                  }`}
                  title="Seasonality (0.35)"
                >
                  S
                </div>
                {/* Arrival Dot */}
                <div 
                  onClick={() => handleAgentClick('arrival', arrivalStatus)}
                  className={`w-8 h-8 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-[10px] font-mono transition-all duration-300 ${
                    arrivalStatus !== 'idle' ? 'border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.3)] text-emerald-400 cursor-pointer hover:border-indigo-500/80 hover:text-white' : 'text-slate-600'
                  }`}
                  title="Arrival (0.40)"
                >
                  A
                </div>
                {/* External Dot */}
                <div 
                  onClick={() => handleAgentClick('external', externalStatus)}
                  className={`w-8 h-8 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-[10px] font-mono transition-all duration-300 ${
                    externalStatus !== 'idle' ? 'border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.3)] text-emerald-400 cursor-pointer hover:border-indigo-500/80 hover:text-white' : 'text-slate-600'
                  }`}
                  title="External (0.25)"
                >
                  E
                </div>
              </div>

              {/* Connecting glowing SVG Lines */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
                {/* Line S to central */}
                <path 
                  d="M 32 16 L 220 72" 
                  fill="none" 
                  stroke={seasonalityStatus === 'completed' ? '#10b981' : '#1e293b'} 
                  strokeWidth="1.5" 
                  strokeDasharray={seasonalityStatus === 'active' ? '4 4' : 'none'}
                  className={seasonalityStatus === 'active' ? 'animate-[dash_2s_linear_infinite]' : ''}
                />
                {/* Line A to central */}
                <path 
                  d="M 32 72 L 220 72" 
                  fill="none" 
                  stroke={arrivalStatus === 'completed' ? '#10b981' : '#1e293b'} 
                  strokeWidth="1.5"
                  strokeDasharray={arrivalStatus === 'active' ? '4 4' : 'none'}
                  className={arrivalStatus === 'active' ? 'animate-[dash_2s_linear_infinite]' : ''}
                />
                {/* Line E to central */}
                <path 
                  d="M 32 128 L 220 72" 
                  fill="none" 
                  stroke={externalStatus === 'completed' ? '#10b981' : '#1e293b'} 
                  strokeWidth="1.5"
                  strokeDasharray={externalStatus === 'active' ? '4 4' : 'none'}
                  className={externalStatus === 'active' ? 'animate-[dash_2s_linear_infinite]' : ''}
                />
              </svg>

              {/* Central Ensemble Fusion Node */}
              <div className="z-10">
                <div 
                  onClick={() => handleAgentClick('ensemble', ensembleStatus)}
                  className={`w-14 h-14 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center transition-all duration-500 ${
                    ensembleStatus === 'active'
                      ? 'border-indigo-500 animate-pulse shadow-[0_0_25px_rgba(99,102,241,0.4)] text-indigo-400 scale-105 cursor-pointer hover:border-indigo-400'
                      : ensembleStatus === 'completed'
                      ? 'border-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.3)] text-emerald-400 scale-100 cursor-pointer hover:border-indigo-500/80 hover:text-indigo-400'
                      : 'text-slate-600'
                  }`}
                >
                  <Layers className="w-7 h-7" />
                </div>
              </div>

            </div>

            {/* Dynamic Status Output Box */}
            <div 
              onClick={() => handleAgentClick('ensemble', ensembleStatus)}
              className={`w-full max-w-sm rounded-xl p-3 border border-slate-900 bg-slate-950/80 text-center font-mono text-[11px] transition-all duration-300 ${mTheme.border} ${
                ensembleStatus !== 'idle' ? 'cursor-pointer hover:border-indigo-500/60' : ''
              }`}
            >
              {ensembleStatus === 'idle' && (
                <span className="text-slate-500">Awaiting Agent Vote Inputs...</span>
              )}
              {ensembleStatus === 'active' && (
                <span className="text-indigo-400 animate-pulse font-bold">FUSING AGENT DECISIONS (S + A + E)...</span>
              )}
              {ensembleStatus === 'completed' && (
                <div className="space-y-1">
                  <div className="text-emerald-400 font-bold uppercase tracking-wider">Meta Ensemble Fused (Click to view graph)</div>
                  <div className="text-slate-400">
                    Confidence: <strong className="text-slate-200">84%</strong> | Recommendation: <strong className="text-slate-200">HOLD</strong>
                  </div>
                </div>
              )}
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
