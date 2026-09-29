'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, RotateCcw, Brain, Cpu, Terminal, Sparkles, CheckCircle } from 'lucide-react';
import EvaluatorSection from './EvaluatorSection';
import EvaluatorFlowNode from './EvaluatorFlowNode';
import EvaluatorFlowConnection from './EvaluatorFlowConnection';
import AgentActivationPanel from './AgentActivationPanel';
import ModelStackView from './ModelStackView';
import AgentReasoningModal from './AgentReasoningModal';
import RecommendationStory from './RecommendationStory';
import { useDecisionJourney, AgentId, JourneyState } from './hooks/useDecisionJourney';

interface FarmerOSIntelligenceViewProps {
  externalStateOverride?: JourneyState;
  externalCurrentIndex?: number;
  externalLogs?: string[];
  externalRecommendationStoryStep?: number;
  hideControls?: boolean;
}

export default function FarmerOSIntelligenceView({
  externalStateOverride,
  externalCurrentIndex,
  externalLogs,
  externalRecommendationStoryStep,
  hideControls = false,
}: FarmerOSIntelligenceViewProps = {}) {
  const {
    currentState,
    isSimulating,
    isPaused,
    stepProgress,
    runJourney,
    pauseJourney,
    resetJourney,
    replayJourney,
    logs,
    currentStateIndex,
  } = useDecisionJourney();

  const [selectedAgentId, setSelectedAgentId] = useState<AgentId>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const seqTerminalEndRef = useRef<HTMLDivElement>(null);

  // Base simulation start time for logs HH:MM:SS format
  const [baseTime] = useState(() => new Date());

  const getLogTimestamp = (secondsOffset: number) => {
    const d = new Date(baseTime.getTime() + secondsOffset * 1000);
    return d.toTimeString().split(' ')[0]; // HH:MM:SS
  };

  // Computed states based on overrides
  const effectiveState = externalStateOverride !== undefined ? externalStateOverride : currentState;
  const effectiveStateIndex = externalCurrentIndex !== undefined ? externalCurrentIndex : currentStateIndex;
  const effectiveLogs = externalLogs !== undefined ? externalLogs : logs;

  // Scroll to bottom of terminal log as new items are added
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [effectiveLogs]);

  // Scroll sequence logs into view as the step progresses
  useEffect(() => {
    if (seqTerminalEndRef.current) {
      seqTerminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [effectiveStateIndex]);

  // Helper to map offline nodes to their states
  const getOfflineNodeStatus = (index: number) => {
    if (effectiveState === 'IDLE') return 'idle';
    
    // Nodes 0, 1, 2 (Historical Data, Feature Engineering, Model Training) -> OFFLINE_FACTORY (index 1)
    if (index <= 2) {
      if (effectiveStateIndex === 1) return 'active';
      if (effectiveStateIndex > 1) return 'completed';
      return 'dimmed';
    }
    
    // Nodes 3, 4, 5 (Agent Model Training, Meta Ensemble, Model Registry) -> MODEL_REGISTRY (index 2)
    if (effectiveStateIndex === 2) return 'active';
    if (effectiveStateIndex > 2) return 'completed';
    return 'dimmed';
  };

  // Helper to map online nodes to their states
  const getOnlineNodeStatus = (index: number) => {
    if (effectiveState === 'IDLE') return 'idle';

    const nodeStateMapping = [
      3, // Live Data Ingestion -> index 3
      4, // Location Intelligence -> index 4
      5, // Data Processing -> index 5
      6, // Digital Farmer Twin -> index 6
      7, // Multi-Agent Intelligence -> active during 7, 8, 9
      10, // Meta Ensemble -> index 10
      11, // Decision Engine -> index 11
      12, // Infrastructure Discovery -> index 12
      13, // Final Recommendation -> index 13
    ];

    const targetStateIdx = nodeStateMapping[index];

    // Special case for Multi-Agent Intelligence (covers Seasonality 7, Arrival 8, External 9)
    if (index === 4) {
      if (effectiveStateIndex >= 7 && effectiveStateIndex <= 9) return 'active';
      if (effectiveStateIndex > 9) return 'completed';
      return 'dimmed';
    }

    if (effectiveStateIndex === targetStateIdx) return 'active';
    if (effectiveStateIndex > targetStateIdx) return 'completed';
    return 'dimmed';
  };

  // Helper to trigger modal for nodes
  const handleNodeClick = (label: string, section: 'offline' | 'online') => {
    if (effectiveState === 'IDLE') return; // Only allow clicks once simulation has started/run
    
    const lowerLabel = label.toLowerCase();
    if (lowerLabel.includes('agent model') || (lowerLabel.includes('multi-agent') && effectiveStateIndex >= 7)) {
      setSelectedAgentId('seasonality');
    } else if (lowerLabel.includes('meta ensemble') && (effectiveStateIndex >= 2 || (section === 'online' && effectiveStateIndex >= 10))) {
      setSelectedAgentId('ensemble');
    }
  };

  // Sections nodes configuration — rich card content via children
  const offlineNodeDefs = [
    { label: 'Historical Data', description: 'ARCHIVE_INGESTION_STAGE', accentColor: 'emerald' as const },
    { label: 'Feature Engineering', description: 'TRANSFORMATION_STAGE', accentColor: 'emerald' as const },
    { label: 'Model Training', description: 'LEARNING_STAGE', accentColor: 'emerald' as const },
    { label: 'Agent Model Training', description: 'BEHAVIORAL_LEARNING (CLICK TO DRILL DOWN)', accentColor: 'emerald' as const },
    { label: 'Meta Ensemble', description: 'AGGREGATED_STRATEGY (CLICK TO DRILL DOWN)', accentColor: 'emerald' as const },
    { label: 'Model Registry', description: 'REGISTRY_STORAGE', accentColor: 'emerald' as const },
  ];

  const offlineCardContent = (index: number, dimmed: boolean) => {
    const fade = dimmed ? 'opacity-30' : '';
    if (index === 0) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="grid grid-cols-2 gap-1.5">
          {[['Agmarknet Records','5.2M Rows'],['Weather Records','1.8M Samples'],['Festival Calendar','250 Events'],['News Corpus','120K Articles'],['Satellite Obs.','850K Images']].map(([k,v])=>(
            <div key={k} className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5">
              <div className="text-slate-500 text-[8px] leading-none">{k}</div>
              <div className="text-emerald-400 font-black text-xs mt-0.5">{v}</div>
            </div>
          ))}
        </div>
        <div className="flex justify-between pt-1 border-t border-slate-900">
          <span className="text-slate-500">Data Health</span><span className="text-emerald-400 font-bold">98.4%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Coverage</span><span className="text-slate-300 font-bold">2018–2026</span>
        </div>
      </div>
    );
    if (index === 1) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest mb-1">Feature Generation</div>
        <div className="grid grid-cols-2 gap-1.5">
          {[['Price Momentum','42'],['Seasonality','18'],['Arrival','23'],['Weather','14'],['Ext. Signals','31']].map(([k,v])=>(
            <div key={k} className="flex justify-between bg-slate-950 border border-slate-800 rounded-lg px-2 py-1">
              <span className="text-slate-400">{k}</span><span className="text-emerald-400 font-black">{v}</span>
            </div>
          ))}
        </div>
        <div className="flex justify-between border-t border-slate-900 pt-1.5">
          <span className="text-slate-400 font-bold">Total Features</span><span className="text-emerald-400 font-black text-sm">128</span>
        </div>
        <div className="flex items-center gap-1 text-[8px] text-slate-600 pt-0.5">
          {['Raw','Clean','Norm','Synth','Store'].map((s,i,a)=>(
            <React.Fragment key={s}><span className="text-slate-500">{s}</span>{i<a.length-1&&<span className="text-slate-700">→</span>}</React.Fragment>
          ))}
        </div>
      </div>
    );
    if (index === 2) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="grid grid-cols-3 gap-1">
          {[['Seasonality','9'],['Arrival','8'],['External','6']].map(([k,v])=>(
            <div key={k} className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-2 text-center">
              <div className="text-emerald-400 font-black text-lg leading-none">{v}</div>
              <div className="text-slate-500 text-[8px] mt-0.5">{k}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-1 pt-1 border-t border-slate-900">
          {[['Strategy','Walk-Fwd CV'],['Splits','5'],['Avg MAPE','11.8%'],['Models Total','23']].map(([k,v])=>(
            <div key={k} className="flex justify-between text-[9px]">
              <span className="text-slate-500">{k}</span><span className="text-slate-200 font-bold">{v}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-1 flex-wrap pt-1">
          {Array(9).fill(0).map((_,i)=><div key={i} className="w-4 h-4 rounded bg-emerald-500/20 border border-emerald-500/30" />)}
        </div>
      </div>
    );
    if (index === 3) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        {[{name:'Seasonality',models:['STL','RF','XGBoost','LightGBM','Ridge','Lasso','SARIMA','Moving Avg','Lag AR'],count:9},
          {name:'Arrival',models:['Reg. Inflow','Prophet','Random Forest','XGBoost','ElasticNet','ARIMA','AutoARIMA','Holt-Winters'],count:8},
          {name:'External',models:['Policy Classifier','IMD Weather','Diesel Indexer','MSP Filter','Trade Reg.','News Sentiment'],count:6}].map(agent=>(
          <div key={agent.name} className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-slate-200 font-black">{agent.name} Agent</span>
              <span className="text-[8px] text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded">{agent.count} Active</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {agent.models.map(m=><span key={m} className="text-[8px] text-slate-500 bg-slate-900 px-1 py-0.5 rounded">{m}</span>)}
            </div>
          </div>
        ))}
      </div>
    );
    if (index === 4) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest">Fusion Strategy</div>
        {['Inverse-MAPE Weighting','Dynamic Reweighting','EMA Smoothing','Festival Boost Logic','Supply Shock Logic','Regime Detection'].map(s=>(
          <div key={s} className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="text-slate-300">{s}</span>
          </div>
        ))}
      </div>
    );
    if (index === 5) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest">Registered Models</div>
        {[['Seasonality','9'],['Arrival','8'],['External','6'],['Meta Ensemble','1']].map(([k,v])=>(
          <div key={k} className="flex justify-between items-center bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1">
            <span className="text-slate-400">{k}</span>
            <span className="text-emerald-400 font-black">{v}</span>
          </div>
        ))}
        <div className="flex justify-between border-t border-slate-900 pt-1.5">
          <span className="text-slate-400 font-bold">Total Artifacts</span><span className="text-emerald-400 font-black">24</span>
        </div>
        <div className="flex justify-between text-[9px]">
          <span className="text-slate-500">Latest Build</span><span className="text-slate-300">Version 2.1</span>
        </div>
      </div>
    );
    return null;
  };

  const onlineNodeDefs = [
    { label: 'Live Data Ingestion', description: 'STREAM_INGESTION', accentColor: 'cyan' as const },
    { label: 'Location Intelligence', description: 'GEO_SPATIAL_MAPPING', accentColor: 'cyan' as const },
    { label: 'Data Processing', description: 'LIVE_TRANSFORM', accentColor: 'cyan' as const },
    { label: 'Digital Farmer Twin', description: 'FARMER_CONTEXT_TWIN', accentColor: 'cyan' as const },
    { label: 'Multi-Agent Intelligence', description: 'MULTI_AGENT_ACTIVATION (CLICK TO DRILL DOWN)', accentColor: 'cyan' as const },
    { label: 'Meta Ensemble', description: 'DECISION_FUSION (CLICK TO DRILL DOWN)', accentColor: 'cyan' as const },
    { label: 'Decision Engine', description: 'STRATEGY_DECISION', accentColor: 'cyan' as const },
    { label: 'Infrastructure Discovery', description: 'FACILITY_CONNECT', accentColor: 'cyan' as const },
    { label: 'Final Recommendation', description: 'OUTPUT_DISPATCH', accentColor: 'violet' as const },
  ];

  const onlineCardContent = (index: number, dimmed: boolean, active: boolean) => {
    const fade = dimmed ? 'opacity-30' : '';
    const pulse = active ? 'animate-pulse' : '';
    if (index === 0) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="grid grid-cols-2 gap-1 mb-1">
          {[['Commodity','Tomato'],['Market','Kolar'],['Timestamp','Live'],['Protocol','REST/WS']].map(([k,v])=>(
            <div key={k} className="flex justify-between bg-slate-950 border border-slate-800 rounded-lg px-2 py-1">
              <span className="text-slate-500">{k}</span><span className="text-cyan-400 font-bold">{v}</span>
            </div>
          ))}
        </div>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest">Incoming Streams</div>
        {[['Price Feed','✓'],['Arrival Feed','✓'],['Weather Feed','✓'],['News Feed','✓']].map(([k,v])=>(
          <div key={k} className="flex justify-between items-center">
            <span className="text-slate-400">{k}</span>
            <span className={`text-emerald-400 font-black ${pulse}`}>{v} LIVE</span>
          </div>
        ))}
      </div>
    );
    if (index === 1) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        <div className="bg-slate-950 border border-cyan-500/20 rounded-lg px-2.5 py-2 mb-1">
          <div className="text-[8px] text-slate-500 mb-0.5">Selected Mandi</div>
          <div className="text-cyan-400 font-black text-sm">Kolar APMC</div>
        </div>
        {[['District','Kolar'],['State','Karnataka'],['Nearby Mandis','7'],['Weather Zone','S. Interior KA'],['Logistics Radius','120 km']].map(([k,v])=>(
          <div key={k} className="flex justify-between">
            <span className="text-slate-500">{k}</span><span className="text-slate-200 font-bold">{v}</span>
          </div>
        ))}
        <div className="flex justify-center pt-1">
          <div className={`relative w-16 h-16 ${active ? 'opacity-100' : 'opacity-40'}`}>
            <div className="absolute inset-0 rounded-full border border-cyan-500/30" />
            <div className="absolute inset-2 rounded-full border border-cyan-500/20" />
            <div className="absolute inset-4 rounded-full border border-cyan-500/40 bg-cyan-500/5" />
            {active && <div className="absolute inset-0 rounded-full border border-cyan-400/40 animate-ping" />}
            <div className="absolute inset-0 flex items-center justify-center text-cyan-400 text-[9px] font-black">KL</div>
          </div>
        </div>
      </div>
    );
    if (index === 2) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest">Records Processed</div>
        {[['Price Data','3,650'],['Arrival Data','3,650'],['Weather Data','3,650'],['Missing Filled','28'],['Features Built','128']].map(([k,v])=>(
          <div key={k} className="flex justify-between bg-slate-950 border border-slate-800 rounded-lg px-2 py-1">
            <span className="text-slate-400">{k}</span><span className="text-cyan-400 font-bold">{v}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 text-[8px] text-slate-600 pt-1">
          {['Validate','Clean','Norm','Enrich','Build'].map((s,i,a)=>(
            <React.Fragment key={s}><span className="text-slate-500">{s}</span>{i<a.length-1&&<span className="text-slate-700">→</span>}</React.Fragment>
          ))}
        </div>
      </div>
    );
    if (index === 3) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest mb-1">Farmer Profile</div>
        {[['Crop','Tomato'],['Holding','4 Acres'],['Production','22 Tons Est.'],['Risk Profile','Moderate'],['Nearest Storage','12 km'],['Schemes Active','3']].map(([k,v])=>(
          <div key={k} className="flex justify-between bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1">
            <span className="text-slate-500">{k}</span><span className="text-cyan-400 font-bold">{v}</span>
          </div>
        ))}
      </div>
    );
    if (index === 4) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        {[
          {name:'Seasonality Agent', thinking:'Analyzing Cycles...', result:'92% Match · Bullish', done: effectiveStateIndex >= 8},
          {name:'Arrival Agent', thinking:'Analyzing Supply Stress...', result:'89% Match · Hold', done: effectiveStateIndex >= 9},
          {name:'External Agent', thinking:'Scanning News Events...', result:'81% Match · Govt Support', done: effectiveStateIndex >= 10},
        ].map(agent=>(
          <div key={agent.name} className={`bg-slate-950 border rounded-lg px-2.5 py-2 transition-all duration-500 ${agent.done ? 'border-emerald-500/30' : active ? 'border-cyan-500/30' : 'border-slate-800'}`}>
            <div className="text-slate-200 font-black mb-0.5">{agent.name}</div>
            <div className={agent.done ? 'text-emerald-400 font-bold' : `text-cyan-400 ${active ? 'animate-pulse' : ''}`}>
              {agent.done ? agent.result : agent.thinking}
            </div>
          </div>
        ))}
      </div>
    );
    if (index === 5) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest">Weight Transfer</div>
        {[['Seasonality','38%',38],['Arrival','47%',47],['External','15%',15]].map(([k,v,w])=>(
          <div key={k}>
            <div className="flex justify-between mb-0.5"><span className="text-slate-400">{k}</span><span className="text-cyan-400 font-bold">{v}</span></div>
            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
              <div className={`h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-1000 ${active || !dimmed ? '' : 'w-0'}`} style={{width: active || effectiveStateIndex>=10 ? `${w}%` : '0%'}} />
            </div>
          </div>
        ))}
        <div className="border-t border-slate-900 pt-1.5 space-y-1">
          {['Confidence Fusion','Conflict Resolution','Regime Detection'].map(s=>(
            <div key={s} className="flex items-center gap-1.5">
              <div className={`w-1 h-1 rounded-full ${active ? 'bg-cyan-400 animate-pulse' : 'bg-slate-700'}`} />
              <span className="text-slate-500">{s}</span>
            </div>
          ))}
        </div>
      </div>
    );
    if (index === 6) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        <div className="grid grid-cols-2 gap-1">
          <div className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-2 text-center">
            <div className="text-emerald-400 font-black text-lg">+4.7%</div>
            <div className="text-slate-500 text-[8px]">Forecast</div>
          </div>
          <div className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-2 text-center">
            <div className="text-cyan-400 font-black text-lg">84%</div>
            <div className="text-slate-500 text-[8px]">Confidence</div>
          </div>
        </div>
        {[['Conflict Check','Passed ✓'],['Risk Level','Medium'],['Regime','Supply Shock'],['Trend','Bullish']].map(([k,v])=>(
          <div key={k} className="flex justify-between">
            <span className="text-slate-500">{k}</span>
            <span className={v.includes('✓') ? 'text-emerald-400 font-bold' : 'text-slate-200 font-bold'}>{v}</span>
          </div>
        ))}
      </div>
    );
    if (index === 7) return (
      <div className={`space-y-1.5 text-[10px] font-mono ${fade}`}>
        <div className="text-[8px] text-slate-500 uppercase tracking-widest mb-1">Nearby Facilities</div>
        {[['Cold Storage','3 units'],['Warehouses','5 units'],['Processing Units','2 units']].map(([k,v])=>(
          <div key={k} className="flex justify-between bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5">
            <span className="text-slate-400">{k}</span><span className="text-cyan-400 font-bold">{v}</span>
          </div>
        ))}
        <div className="flex justify-between border-t border-slate-900 pt-1.5">
          <span className="text-slate-400 font-bold">Distance Score</span>
          <span className="text-emerald-400 font-black">82%</span>
        </div>
      </div>
    );
    if (index === 8) return (
      <div className={`space-y-2 text-[10px] font-mono ${fade}`}>
        <div className={`text-center py-3 rounded-xl border ${effectiveStateIndex >= 13 ? 'border-emerald-500/40 bg-emerald-950/20' : 'border-slate-800 bg-slate-950'}`}>
          <div className={`text-xl font-black ${effectiveStateIndex >= 13 ? 'text-emerald-400' : 'text-slate-600'}`}>
            {effectiveStateIndex >= 13 ? 'HOLD' : '—'}
          </div>
          <div className="text-slate-500 text-[8px] mt-0.5">Final Action</div>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Commodity</span><span className="text-slate-200 font-bold">Tomato</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Days</span><span className="text-slate-200 font-bold">7 Days</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Gain Est.</span><span className="text-emerald-400 font-bold">₹250/q</span>
        </div>
      </div>
    );
    return null;
  };



  // Dynamic chronological logs mapping
  const sequenceLogs = [
    { step: 3, time: getLogTimestamp(0), event: 'DATA_INGEST', details: 'Real-time market API feeds fetched' },
    { step: 4, time: getLogTimestamp(1), event: 'GEO_SPATIAL', details: 'Bangalore Yeshwanthpur mandi coordinates resolved' },
    { step: 6, time: getLogTimestamp(2), event: 'CONTEXT_TWIN', details: 'Digital Twin attributes and features engineering generated' },
    { step: 7, time: getLogTimestamp(3), event: 'MULTI_AGENT', details: 'Multi-Agent forecasting sub-models triggered' },
    { step: 10, time: getLogTimestamp(4), event: 'META_ENSEMBLE', details: 'Meta Ensemble dynamic weight fusion executed' },
    { step: 11, time: getLogTimestamp(5), event: 'DECISION_ENGINE', details: 'Decision Engine strategic action resolved' },
    { step: 13, time: getLogTimestamp(6), event: 'RECOMMENDATION', details: 'Final recommendation compiled and sent to storyboard' },
  ];

  return (
    <div className="w-full min-h-screen bg-[#05080e] text-slate-100 flex flex-col relative overflow-hidden font-sans pb-16">
      {/* Background grid and ornaments */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#48d0ff_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="absolute top-1/3 left-1/4 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Main Header (Rendered only if not controlled externally) */}
      {!externalStateOverride && (
        <header className="relative z-10 border-b border-slate-900 bg-slate-950/40 backdrop-blur-md px-6 py-6 md:px-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.25em] text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-400/20 uppercase font-mono animate-pulse">
                <Brain className="w-3.5 h-3.5" />
                FarmerOS Intelligence Registry
              </span>
              <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.25em] text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-400/20 uppercase font-mono">
                <Cpu className="w-3.5 h-3.5" />
                Observability Model
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-black text-slate-100 tracking-tighter">
              Inside the Brain of FarmerOS
            </h1>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed font-sans">
              Evaluator-facing visualization explaining model architectures, offline training registries, and execution reasoning paths.
            </p>
          </div>

          {/* Observability Status */}
          <div className="flex items-center gap-3.5 bg-slate-950/80 border border-slate-900 px-5 py-3.5 rounded-2xl">
            <div className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isSimulating ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className={`relative inline-flex rounded-full h-2 w-2 ${isSimulating ? 'bg-emerald-500' : 'bg-slate-600'}`} />
            </div>
            <div className="font-mono text-left">
              <span className="block text-[8px] text-slate-500 uppercase tracking-widest leading-none">System Observability Status</span>
              <span className="text-[10px] font-bold text-slate-300">
                {currentState === 'IDLE' ? 'IDLE: WAITING_FOR_SIMULATION' : isPaused ? 'PAUSED: SIMULATION_HALTED' : 'ACTIVE: JOURNEY_RUNNING'}
              </span>
            </div>
          </div>
        </header>
      )}

      {/* Main Container */}
      <main className="relative z-10 px-6 md:px-8 py-8 space-y-10 max-w-7xl mx-auto w-full">
        
        {/* CONTROL CENTER & TERMINAL SPLIT PANEL */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          
          {/* Controls Box (5 columns) */}
          {!hideControls && (
            <div className="lg:col-span-5 bg-[#09101d]/90 backdrop-blur-xl border border-slate-900 rounded-[2rem] p-6 flex flex-col justify-between shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />
              
              <div className="space-y-4">
                <div>
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest block mb-1">
                    Simulation Controller
                  </span>
                  <h3 className="text-base font-black text-slate-100 tracking-tight">
                    Decision Journey Control Unit
                  </h3>
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-3">
                  <div className="grid grid-cols-2 gap-3">
                    {!isSimulating || isPaused ? (
                      <button
                        onClick={runJourney}
                        className="py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wider uppercase transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)] flex items-center justify-center gap-2 active:scale-[0.98]"
                      >
                        <Play className="w-3.5 h-3.5 fill-current" />
                        {currentState === 'COMPLETE' ? 'Re-Run System' : 'Run Journey'}
                      </button>
                    ) : (
                      <button
                        onClick={pauseJourney}
                        className="py-3 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs tracking-wider uppercase transition-all shadow-[0_0_15px_rgba(245,158,11,0.2)] flex items-center justify-center gap-2 active:scale-[0.98]"
                      >
                        <Pause className="w-3.5 h-3.5 fill-current" />
                        Pause Journey
                      </button>
                    )}

                    <button
                      onClick={replayJourney}
                      disabled={currentState === 'IDLE'}
                      className="py-3 px-4 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-slate-200 font-bold text-xs tracking-wider uppercase transition-all flex items-center justify-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Replay
                    </button>
                  </div>

                  <button
                    onClick={resetJourney}
                    disabled={currentState === 'IDLE'}
                    className="w-full py-2.5 rounded-xl border border-slate-900 bg-slate-950/40 hover:bg-slate-900/60 text-slate-500 hover:text-slate-350 font-semibold text-xs tracking-wider uppercase transition-all flex items-center justify-center gap-1.5 disabled:opacity-20 disabled:cursor-not-allowed"
                  >
                    Reset Simulation
                  </button>
                </div>
              </div>

              {/* Simulation progress indicators */}
              <div className="border-t border-slate-900/80 pt-4 mt-6 space-y-2.5">
                <div className="flex justify-between items-center font-mono text-[10px] text-slate-500">
                  <span>SIMULATION_STAGE:</span>
                  <span className="text-cyan-400 font-bold uppercase">{currentState}</span>
                </div>
                
                {/* Progress bar container */}
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-900/40">
                  <div 
                    className="bg-gradient-to-r from-cyan-500 to-emerald-500 h-full rounded-full transition-all duration-100 ease-out" 
                    style={{ width: `${currentState === 'COMPLETE' ? 100 : currentState === 'IDLE' ? 0 : stepProgress}%` }}
                  />
                </div>

                <div className="flex justify-between items-center text-[9px] font-mono text-slate-650">
                  <span>STAGE_PROGRESS:</span>
                  <span>{currentState === 'COMPLETE' ? '100%' : currentState === 'IDLE' ? '0%' : `${Math.floor(stepProgress)}%`}</span>
                </div>
              </div>

            </div>
          )}

          {/* Terminal log panel (7 columns normally, 12 columns if controls are hidden) */}
          <div className={`${hideControls ? 'lg:col-span-12' : 'lg:col-span-7'} bg-black/85 border border-slate-900 rounded-[2rem] p-5 flex flex-col justify-between shadow-[inset_0_2px_8px_rgba(0,0,0,0.8)] font-mono relative min-h-[250px]`}>
            <div className="absolute top-2 right-4 flex items-center gap-1.5 opacity-60">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[9px] text-slate-500">TELEMETRY_LOGS</span>
            </div>

            <div className="w-full h-full overflow-y-auto max-h-[220px] text-xs space-y-2 pr-2 scrollbar-thin scrollbar-thumb-slate-800">
              {effectiveLogs.map((log, index) => {
                let colorClass = 'text-slate-400';
                if (log.includes('active') || log.includes('Connected') || log.includes('Completed')) {
                  colorClass = 'text-emerald-400 font-semibold';
                } else if (log.includes('RECOMMENDATION') || log.includes('HOLD') || log.includes('₹250') || log.includes('DECISION READY')) {
                  colorClass = 'text-cyan-300 font-black';
                } else if (log.startsWith('Initializing') || log.includes('activated') || log.includes('executing')) {
                  colorClass = 'text-indigo-400 font-semibold';
                }

                return (
                  <div key={index} className="flex gap-2 items-start leading-relaxed">
                    <span className="text-slate-600 select-none">&gt;</span>
                    <p className={colorClass}>{log}</p>
                  </div>
                );
              })}
              <div ref={terminalEndRef} />
            </div>

            <div className="border-t border-slate-900 pt-3 mt-3 flex justify-between items-center text-[9px] text-slate-505">
              <span>OUTPUT_CHANNEL: EVALUATOR_TELEMETRY</span>
              <span>LINES: {effectiveLogs.length}</span>
            </div>
          </div>

        </div>

        {/* SECTION A: Offline Intelligence Factory */}
        <EvaluatorSection
          title="STAGE A // PRE-COMPUTATION"
          subtitle="Offline Intelligence Factory"
          purpose="Details the offline model construction pipelines executed before user interaction. Shows historical data compilation, training sub-agents, and ensemble configuration stored in the Model Registry."
          accentColor="emerald"
        >
          <div className="flex flex-col md:flex-row md:flex-wrap items-stretch justify-start gap-4">
            {offlineNodeDefs.map((node, index) => {
              const jStatus = getOfflineNodeStatus(index);
              const isClickable = index === 3 || index === 4;
              return (
                <React.Fragment key={index}>
                  <EvaluatorFlowNode 
                    {...node} 
                    journeyStatus={jStatus} 
                    onSelect={isClickable && jStatus !== 'idle' ? () => handleNodeClick(node.label, 'offline') : undefined}
                  >
                    {offlineCardContent(index, jStatus === 'dimmed')}
                  </EvaluatorFlowNode>
                  {index < offlineNodeDefs.length - 1 && (
                    <EvaluatorFlowConnection accentColor="emerald" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </EvaluatorSection>

        {/* SECTION B: Online Prediction Flow */}
        <EvaluatorSection
          title="STAGE B // RUNTIME RESOLUTION"
          subtitle="Online Prediction Flow"
          purpose="Illustrates the step-by-step pipeline executed when a farmer queries the OS. Real-time ingestion builds the context twin, triggers agent voting, executes ensemble reasoning, and outputs recommendations."
          accentColor="cyan"
        >
          <div className="flex flex-col md:flex-row md:flex-wrap items-stretch justify-start gap-4">
            {onlineNodeDefs.map((node, index) => {
              const jStatus = getOnlineNodeStatus(index);
              const isClickable = index === 4 || index === 5;
              const isActive = jStatus === 'active';
              return (
                <React.Fragment key={index}>
                  <EvaluatorFlowNode 
                    {...node} 
                    journeyStatus={jStatus} 
                    onSelect={isClickable && jStatus !== 'idle' && jStatus !== 'dimmed' ? () => handleNodeClick(node.label, 'online') : undefined}
                  >
                    {onlineCardContent(index, jStatus === 'dimmed', isActive)}
                  </EvaluatorFlowNode>
                  {index < onlineNodeDefs.length - 1 && (
                    <EvaluatorFlowConnection accentColor={node.accentColor === 'violet' ? 'violet' : 'cyan'} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </EvaluatorSection>




        {/* MODEL STACK DIAGNOSTICS ASSEMBLY (COLLAPSIBLE CARD) */}
        <ModelStackView />

        {/* AGENT ACTIVATION PANEL */}
        <AgentActivationPanel currentState={effectiveState} onSelectAgent={setSelectedAgentId} />

        {/* REVEAL DECISION READY CARD (Slides/fades in when final step is active/complete) */}
        <div className="w-full transition-all duration-75">
          {effectiveStateIndex >= 13 ? (
            <div className="w-full bg-slate-950 border-2 border-emerald-500/80 rounded-[2.5rem] p-8 shadow-[0_0_40px_rgba(16,185,129,0.25)] relative overflow-hidden animate-[revealCard_0.8s_ease-out_both]">
              <style dangerouslySetInnerHTML={{__html: `
                @keyframes revealCard {
                  from { opacity: 0; transform: translateY(20px); }
                  to { opacity: 1; transform: translateY(0); }
                }
              `}} />
              {/* Background ambient radial */}
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.06),transparent_60%)] pointer-events-none" />

              <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-8">
                <div className="space-y-3.5 text-center lg:text-left">
                  <div className="flex items-center justify-center lg:justify-start gap-2.5">
                    <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold tracking-[0.25em] text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-400/20 uppercase font-mono">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                      Status: Execution Complete
                    </span>
                  </div>
                  <h3 className="text-3xl font-black text-slate-100 tracking-tight">DECISION READY</h3>
                  <p className="text-sm text-slate-455 max-w-2xl leading-relaxed">
                    The Meta Ensemble has successfully compiled all active forecasting models. The final resolved recommendation is dispatched to the storyboard below.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="w-full bg-slate-950/30 border border-slate-900 rounded-[2.5rem] p-8 text-center text-slate-550 flex flex-col items-center justify-center py-16 gap-3">
              <Sparkles className="w-8 h-8 text-slate-700 animate-pulse" />
              <div>
                <h4 className="text-sm font-bold text-slate-450">Awaiting Recommendation Synthesis</h4>
                <p className="text-xs text-slate-600 mt-1 max-w-sm mx-auto leading-relaxed">
                  Run the simulation to trigger data twins and agent fusion. The final recommendation status will reveal here.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* RECOMMENDATION GENERATION STORYBOARD */}
        <RecommendationStory stepOverride={externalRecommendationStoryStep} />

        {/* SECTION C: Reasoning Sequence Logs */}
        <EvaluatorSection
          title="STAGE C // SEQUENCE LOGS"
          subtitle="Reasoning Sequence Logs"
          purpose="A compact chronological sequence log trace showing order of execution. Follows raw input mapping through feature engineering, multi-agent evaluation, and decision synthesis."
          accentColor="violet"
        >
          <div className="w-full bg-black/80 border border-slate-900 rounded-[2rem] p-5 font-mono relative min-h-[160px] shadow-[inset_0_2px_8px_rgba(0,0,0,0.8)]">
            <div className="absolute top-4 right-5 flex items-center gap-1.5 opacity-60">
              <Terminal className="w-3.5 h-3.5 text-violet-400" />
              <span className="text-[9px] text-slate-500">CHRONO_SEQUENCE_LOGS</span>
            </div>

            <div className="space-y-2.5 max-h-[125px] overflow-y-auto text-xs pr-2 scrollbar-thin scrollbar-thumb-slate-800">
              {sequenceLogs
                .filter(log => effectiveStateIndex >= log.step)
                .map((log, idx) => (
                  <div key={idx} className="flex gap-3 items-start leading-relaxed text-slate-400">
                    <span className="text-slate-600 select-none">[{log.time}]</span>
                    <span className="text-violet-400 font-bold">[{log.event}]</span>
                    <p className="text-slate-300">{log.details}</p>
                    <span className="text-emerald-400 ml-auto font-bold uppercase text-[9px] tracking-widest bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-400/20">RESOLVED</span>
                  </div>
                ))}
              {effectiveStateIndex < 3 && (
                <div className="text-slate-600 text-xs italic">Awaiting simulation execution to generate sequence logs...</div>
              )}
              <div ref={seqTerminalEndRef} />
            </div>
          </div>
        </EvaluatorSection>

      </main>

      {/* AGENT DIAGNOSTICS MODAL PORTAL */}
      <AgentReasoningModal agentId={selectedAgentId} onClose={() => setSelectedAgentId(null)} />

      {/* Disclaimers Footer */}
      {!externalStateOverride && (
        <footer className="relative z-10 max-w-7xl mx-auto w-full px-6 md:px-8 text-center text-[10px] font-mono text-slate-600 border-t border-slate-900 pt-6">
          <span>FARMEROS INTEL VIEW // SYSTEM MODEL OBSERVABILITY SCHEMA VER 1.2.4</span>
          <span className="block mt-1">NO DATA RETENTION // READ-ONLY SIMULATION CONTAINER</span>
        </footer>
      )}
    </div>
  );
}
