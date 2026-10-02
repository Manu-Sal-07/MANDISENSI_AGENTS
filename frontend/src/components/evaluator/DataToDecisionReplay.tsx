'use client';

import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, SkipForward, Sparkles, Brain, Cpu, Terminal, Database, Layers } from 'lucide-react';
import FarmerOSIntelligenceView from './FarmerOSIntelligenceView';
import { JourneyState } from './hooks/useDecisionJourney';

interface StageConfig {
  id: number;
  name: string;
  timelineGroup: string;
  journeyState: JourneyState;
  stateIndex: number;
  recommendationStoryStep: number;
  duration: number; // in ms
  logs: string[];
  explanation: {
    title: string;
    subtitle: string;
    details: string;
    techStack: string;
  };
}

const STAGES: StageConfig[] = [
  {
    id: 1,
    name: 'Historical Data Ingestion',
    timelineGroup: 'Historical Data',
    journeyState: 'OFFLINE_FACTORY',
    stateIndex: 1,
    recommendationStoryStep: 0,
    duration: 3500,
    logs: [
      'Initializing Offline Intelligence Factory...',
      'Inflow Thread: Connecting to Agmarknet Tomato daily price logs (2018-2026).',
      'Weather Thread: Ingesting IMD historical daily precipitation database.',
      'Socio-Policy Thread: Parsing MSP incentives and export restriction tables.',
      'Satellite Thread: Normalizing raw NDVI crop vegetation indexes.',
      'Completed historical archive caching (142,000 observations).'
    ],
    explanation: {
      title: 'Historical Data Ingestion',
      subtitle: 'STAGE 1: OFFLINE INGESTION',
      details: 'FarmerOS aggregates multiple sources to build deep contextual awareness of price patterns before prediction runtime.',
      techStack: 'Python, Pandas Ingestion'
    }
  },
  {
    id: 2,
    name: 'Offline Model Training',
    timelineGroup: 'Training',
    journeyState: 'OFFLINE_FACTORY',
    stateIndex: 1,
    recommendationStoryStep: 0,
    duration: 3500,
    logs: [
      'Starting batch estimator training pipelines...',
      'Seasonality Agent: Training 9 ARIMA & Prophet estimators on Agmarknet cycles.',
      'Arrival Agent: Fitting 8 regression estimators on regional Mandi inflows.',
      'External Agent: Tuning 6 Logistic & Sentiment models on news and weather trends.',
      'Computing initial Meta Ensemble weights matrix.'
    ],
    explanation: {
      title: 'Offline Model Training',
      subtitle: 'STAGE 2: ESTIMATOR COUPLING',
      details: 'All 23 sub-models are trained, validated, and fine-tuned offline in parallel threads to achieve baseline parameter weights.',
      techStack: 'Scikit-Learn, Statsmodels'
    }
  },
  {
    id: 3,
    name: 'Model Registry Deployment',
    timelineGroup: 'Registry',
    journeyState: 'MODEL_REGISTRY',
    stateIndex: 2,
    recommendationStoryStep: 0,
    duration: 3000,
    logs: [
      'All 23 sub-model artifacts serialized.',
      'Exporting state dictionary models to registry storage...',
      'Registry Status: ONLINE. Validation pass succeeded.',
      'System ready to accept live queries.'
    ],
    explanation: {
      title: 'Model Registry Deployment',
      subtitle: 'STAGE 3: PRODUCTION REGISTRY',
      details: 'Completed model weights are frozen and stored in the model registry container, ready for fast execution queries.',
      techStack: 'Local Serialization, JSON Registry'
    }
  },
  {
    id: 4,
    name: 'Live Context Twin Building',
    timelineGroup: 'Live Data',
    journeyState: 'LOCATION_INTELLIGENCE',
    stateIndex: 4,
    recommendationStoryStep: 0,
    duration: 3000,
    logs: [
      'Intercepted live user query: MANDI_PRICE_FORECAST.',
      'Geospatial Proximity Match: Bangalore Yeshwanthpur Mandi recognized.',
      'Locating active farmer crop profile: Tomato crop type, sowing stage.',
      'Constructing Digital Farmer Twin context metadata...'
    ],
    explanation: {
      title: 'Live Context Twin Building',
      subtitle: 'STAGE 4: LOCATION INTELLIGENCE',
      details: 'When a query arrives, the system constructs a digital representation of the farmer, mapping crop data, location, and weather.',
      techStack: 'Haversine Coordinates Mapping'
    }
  },
  {
    id: 5,
    name: 'Live Data Stream Ingestion',
    timelineGroup: 'Live Data',
    journeyState: 'LIVE_INGESTION',
    stateIndex: 3,
    recommendationStoryStep: 0,
    duration: 3000,
    logs: [
      'Streaming live telemetry parameters...',
      'Connected to real-time market API feeds.',
      'Ingesting current local mandi pricing indicators.',
      'Live stream packet parsed and normalized: SUCCESS.'
    ],
    explanation: {
      title: 'Live Data Stream Ingestion',
      subtitle: 'STAGE 5: REAL-TIME STREAMING',
      details: 'Active market inflows and weather feeds are fetched live, then pre-processed to align with offline training dimensions.',
      techStack: 'REST API, JSON Ingestion'
    }
  },
  {
    id: 6,
    name: 'Multi-Agent Execution',
    timelineGroup: 'Agents',
    journeyState: 'SEASONALITY_ANALYSIS',
    stateIndex: 7,
    recommendationStoryStep: 0,
    duration: 4000,
    logs: [
      'Invoking active Multi-Agent forecasting layer...',
      'Seasonality Agent activated (9 models executing, forecast +4.2%).',
      'Arrival Agent activated (8 models executing, forecast +5.1%).',
      'External Agent activated (6 models executing, forecast -0.7%).',
      'All agents completed local voting.'
    ],
    explanation: {
      title: 'Multi-Agent Execution',
      subtitle: 'STAGE 6: MODEL EXECUTION',
      details: 'Seasonality, Arrival, and External agents activate. Each agent processes inputs across its dedicated set of ML models.',
      techStack: 'FastAPI Router'
    }
  },
  {
    id: 7,
    name: 'Evidence Streaming',
    timelineGroup: 'Fusion',
    journeyState: 'META_ENSEMBLE',
    stateIndex: 10,
    recommendationStoryStep: 3,
    duration: 4500,
    logs: [
      'Streaming individual agent predictions to the Meta Ensemble...',
      'Seasonality evidence registered (+4.2% price rise suggested).',
      'Arrival evidence registered (+5.1% supply constraint suggested).',
      'External evidence registered (-0.7% weather margin buffer suggested).'
    ],
    explanation: {
      title: 'Evidence Streaming',
      subtitle: 'STAGE 7: DATASTREAM ROUTING',
      details: 'Individual agent forecasts are routed towards the Meta Ensemble. Watch the animated data packets traverse connecting paths.',
      techStack: 'React, SVG Rendering'
    }
  },
  {
    id: 8,
    name: 'Meta Ensemble',
    timelineGroup: 'Fusion',
    journeyState: 'META_ENSEMBLE',
    stateIndex: 10,
    recommendationStoryStep: 4,
    duration: 4000,
    logs: [
      'Meta Ensemble executing...',
      'Evaluating Weighted Fusion (Weights: Seasonality 38% / Arrival 47% / External 15%).',
      'Evaluating Confidence Fusion metrics.',
      'Resolving prediction conflicts (High confidence agreement detected).',
      'Assessing risk factor thresholds.'
    ],
    explanation: {
      title: 'Meta Ensemble',
      subtitle: 'STAGE 8: WEIGHTED REGIME FUSION',
      details: 'The Meta Ensemble resolves conflicting inputs from sub-agents using dynamic weight adaptation based on current market regimes.',
      techStack: 'NumPy, Weights Matrix'
    }
  },
  {
    id: 9,
    name: 'Decision Synthesis',
    timelineGroup: 'Decision',
    journeyState: 'DECISION_ENGINE',
    stateIndex: 11,
    recommendationStoryStep: 5,
    duration: 3500,
    logs: [
      'Consolidation result passed to Decision Engine.',
      'Fused Forecast: +4.7% price trend trajectory.',
      'Fused Confidence Score: 84%.',
      'Matching infrastructure options: Checking cold storage capacities...'
    ],
    explanation: {
      title: 'Decision Synthesis',
      subtitle: 'STAGE 9: STRATEGIC ACTION SELECTION',
      details: 'The fused prediction trend is analyzed against local infrastructure options to yield a concrete optimization suggestion.',
      techStack: 'Optimization Heuristics'
    }
  },
  {
    id: 10,
    name: 'Action Recommendation',
    timelineGroup: 'Recommendation',
    journeyState: 'COMPLETE',
    stateIndex: 13,
    recommendationStoryStep: 6,
    duration: 0,
    logs: [
      'Optimal strategy identified: HOLD tomato stock.',
      'Decision state: Decision compiled. Action dispatched to storyboard.',
      'Explainability parameters compiled. Observability run complete.'
    ],
    explanation: {
      title: 'Action Recommendation',
      subtitle: 'STAGE 10: RECOMMENDATION READY',
      details: 'The final action recommendation is resolved and dispatched. The explainability logs provide full transparency to evaluators.',
      techStack: 'REST Dispatcher'
    }
  }
];

const TIMELINE_GROUPS = [
  'Historical Data',
  'Training',
  'Registry',
  'Live Data',
  'Agents',
  'Fusion',
  'Decision',
  'Recommendation'
];

export default function DataToDecisionReplay() {
  const [stageIdx, setStageIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isAutoDemo, setIsAutoDemo] = useState<boolean>(true);
  const [cumulativeLogs, setCumulativeLogs] = useState<string[]>([]);

  const activeStage = STAGES[stageIdx];

  // Map active stage to timeline group highlight state
  const getGroupStatus = (group: string) => {
    const activeGroup = activeStage.timelineGroup;
    const activeGroupIdx = TIMELINE_GROUPS.indexOf(activeGroup);
    const targetGroupIdx = TIMELINE_GROUPS.indexOf(group);

    if (targetGroupIdx < activeGroupIdx) return 'completed';
    if (targetGroupIdx === activeGroupIdx) return 'active';
    return 'pending';
  };

  // Build cumulative logs up to current stage
  useEffect(() => {
    let logsAccumulator: string[] = [];
    for (let i = 0; i <= stageIdx; i++) {
      logsAccumulator = [...logsAccumulator, ...STAGES[i].logs];
    }
    setCumulativeLogs(logsAccumulator);
  }, [stageIdx]);

  // Handle Play/Pause timer loop
  useEffect(() => {
    if (!isPlaying) return;

    // If we reached the end, loop back or stop
    if (stageIdx >= STAGES.length - 1) {
      setIsPlaying(false);
      return;
    }

    const currentDuration = STAGES[stageIdx].duration;
    const timer = setTimeout(() => {
      setStageIdx(prev => Math.min(prev + 1, STAGES.length - 1));
    }, currentDuration);

    return () => clearTimeout(timer);
  }, [isPlaying, stageIdx]);

  const handlePlay = () => {
    if (stageIdx === STAGES.length - 1) {
      // Restart if play is clicked at the end
      setStageIdx(0);
    }
    setIsPlaying(true);
  };

  const handlePause = () => {
    setIsPlaying(false);
  };

  const handleRestart = () => {
    setIsPlaying(false);
    setStageIdx(0);
  };

  const handleSkip = () => {
    setIsPlaying(false);
    setStageIdx(prev => Math.min(prev + 1, STAGES.length - 1));
  };

  const jumpToStage = (idx: number) => {
    setIsPlaying(false);
    setStageIdx(idx);
  };

  return (
    <div className="w-full min-h-screen bg-[#05080e] relative flex flex-col justify-between">
      
      {/* TIMELINE PROGRESS BAR (Sticky Top Header) */}
      <div className="sticky top-0 z-50 w-full bg-[#05080e]/95 backdrop-blur-xl border-b border-slate-900/80 px-6 py-4.5 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          <div>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.25em] text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-400/20 uppercase font-mono animate-pulse">
                <Brain className="w-3.5 h-3.5" />
                Data-To-Decision Replay System
              </span>
              {isAutoDemo && (
                <span className="flex items-center gap-1 text-[8.5px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 uppercase">
                  <Sparkles className="w-3 h-3 animate-spin" />
                  Auto-Explain Active
                </span>
              )}
            </div>
            <h2 className="text-sm font-black text-slate-100 uppercase tracking-wider mt-1.5">
              Netflix Playback of FarmerOS Intelligence
            </h2>
          </div>

          {/* Replay Timeline Segments */}
          <div className="flex items-center gap-1.5 md:gap-3 flex-wrap">
            {TIMELINE_GROUPS.map((group, idx) => {
              const status = getGroupStatus(group);
              // Map group name to first stage index belonging to it
              const firstStageIdx = STAGES.findIndex(s => s.timelineGroup === group);

              let colorClass = 'border-slate-800 text-slate-500 bg-slate-950/10';
              if (status === 'completed') {
                colorClass = 'border-emerald-500/50 text-emerald-400 bg-emerald-950/10 hover:border-emerald-400';
              } else if (status === 'active') {
                colorClass = 'border-cyan-500 text-cyan-400 bg-cyan-950/20 shadow-[0_0_10px_rgba(6,182,212,0.15)] font-bold animate-pulse hover:border-cyan-400';
              }

              return (
                <button
                  key={idx}
                  onClick={() => jumpToStage(firstStageIdx)}
                  className={`border rounded-xl px-2.5 py-1.5 text-[9px] font-mono transition-all duration-300 uppercase cursor-pointer hover:bg-slate-900/40 ${colorClass}`}
                >
                  [{group}]
                </button>
              );
            })}
          </div>

        </div>
      </div>

      {/* PIPELINE MENTAL MAP (How FarmerOS Thinks Header) */}
      <div className="max-w-7xl mx-auto w-full px-6 md:px-8 pt-6">
        <div className="bg-[#09101d]/60 border border-slate-900 rounded-[2rem] p-5 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
          <span className="block text-[8.5px] font-mono text-slate-500 uppercase tracking-[0.25em] mb-3 text-center">
            Decision Pipeline Map // How FarmerOS Thinks
          </span>
          <div className="flex flex-wrap items-center justify-center gap-2 md:gap-4 text-[10px] font-mono text-slate-400">
            <span className="bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-900">Historical Data</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-900">Model Training</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-900">Live Farmer Context</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-900">Multi-Agent Reasoning</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-indigo-950/40 px-2.5 py-1.5 rounded-xl border border-indigo-900/40 text-indigo-400 font-bold">Meta Ensemble</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-900">Decision Generation</span>
            <span className="text-slate-700">➔</span>
            <span className="bg-emerald-950/40 px-2.5 py-1.5 rounded-xl border border-emerald-900/40 text-emerald-400 font-bold">Action Recommendation</span>
          </div>
        </div>
      </div>

      {/* FLOATING EXPLAINER DIALOGUE (Renders active stage details on the right overlay) */}
      <div className="fixed bottom-28 right-6 z-40 max-w-sm w-full bg-[#09101d]/90 backdrop-blur-xl border border-slate-900 rounded-[2rem] p-5 shadow-2xl animate-[explainerReveal_0.5s_ease-out_both]">
        <style dangerouslySetInnerHTML={{__html: `
          @keyframes explainerReveal {
            from { opacity: 0; transform: translateY(15px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
          }
        `}} />

        <div className="space-y-4">
          <div className="flex justify-between items-start border-b border-slate-900 pb-3">
            <div>
              <span className="text-[8px] font-mono text-slate-500 uppercase tracking-widest">{activeStage.explanation.subtitle}</span>
              <h4 className="text-xs font-black text-slate-100 tracking-tight mt-0.5">{activeStage.explanation.title}</h4>
            </div>
            <span className="text-[10px] font-mono font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-md border border-cyan-500/20">
              Stage {activeStage.id}/10
            </span>
          </div>

          <p className="text-[11px] text-slate-455 leading-relaxed font-sans">
            {activeStage.explanation.details}
          </p>

          <div className="bg-slate-950/60 border border-slate-900/60 rounded-xl p-2.5 flex items-center justify-between text-[8.5px] font-mono">
            <span className="text-slate-550">Tech Stack:</span>
            <span className="text-indigo-400 font-bold">{activeStage.explanation.techStack}</span>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT WRAPPER */}
      <div className="flex-1 w-full relative">
        <FarmerOSIntelligenceView
          externalStateOverride={activeStage.journeyState}
          externalCurrentIndex={activeStage.stateIndex}
          externalLogs={cumulativeLogs}
          externalRecommendationStoryStep={activeStage.recommendationStoryStep}
          hideControls={true}
        />
      </div>

      {/* FLOATING CONTROLLER BAR (Bottom Sticky Bar) */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-xl bg-[#09101d]/95 backdrop-blur-xl border border-slate-900/90 rounded-2xl p-4 shadow-2xl flex items-center justify-between gap-4">
        
        {/* Playback action controls */}
        <div className="flex items-center gap-2">
          {isPlaying ? (
            <button
              onClick={handlePause}
              className="w-10 h-10 rounded-xl bg-amber-600 hover:bg-amber-500 text-white flex items-center justify-center transition-all shadow-[0_0_10px_rgba(245,158,11,0.15)]"
              title="Pause Replay"
            >
              <Pause className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={handlePlay}
              className="w-10 h-10 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center transition-all shadow-[0_0_10px_rgba(16,185,129,0.15)]"
              title="Play Replay"
            >
              <Play className="w-4 h-4 fill-current ml-0.5" />
            </button>
          )}

          <button
            onClick={handleRestart}
            className="w-9 h-9 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-slate-200 flex items-center justify-center transition-all"
            title="Restart Replay"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleSkip}
            disabled={stageIdx >= STAGES.length - 1}
            className="w-9 h-9 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-slate-200 flex items-center justify-center transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            title="Skip to Next Stage"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Stage progress label */}
        <div className="text-center font-mono">
          <span className="block text-[8px] text-slate-500 uppercase tracking-widest leading-none mb-1">Active Playback Stage</span>
          <span className="text-[10px] text-slate-350 font-bold truncate max-w-[150px] block">{activeStage.name}</span>
        </div>

        {/* Auto Demo switch control */}
        <button
          onClick={() => setIsAutoDemo(prev => !prev)}
          className={`py-2 px-3.5 rounded-xl text-[10px] font-bold tracking-wider uppercase transition-all flex items-center gap-1.5 ${
            isAutoDemo 
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_12px_rgba(99,102,241,0.2)]' 
              : 'border border-slate-800 hover:bg-slate-900 text-slate-500 hover:text-slate-300'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Auto Demo
        </button>

      </div>

    </div>
  );
}
