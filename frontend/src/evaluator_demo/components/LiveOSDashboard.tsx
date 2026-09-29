import React, { useState, useEffect } from 'react';
import { Terminal, CheckCircle2, Compass, Layers } from 'lucide-react';
import DataPacket from './DataPacket';
import PacketRouter from './PacketRouter';
import LiveOSAgentCard from './LiveOSAgentCard';
import FusionOrbit from './FusionOrbit';
import DecisionBuilder from './DecisionBuilder';
import ExecutionTimeline from './ExecutionTimeline';
import DecisionDNAChart from './DecisionDNAChart';
import InfluenceRanking from './InfluenceRanking';
import DecisionScoreAnimator from './DecisionScoreAnimator';
import AnimatedCard from './AnimatedCard';

import { MockAnalysisResult } from './MockAnalysisProvider';

interface LiveOSDashboardProps {
  stepId: number;
  progress: number;
  queryText: string;
  tokens: string[];
  analysisResult: MockAnalysisResult;
}

export default function LiveOSDashboard({
  stepId,
  progress,
  queryText,
  tokens,
  analysisResult
}: LiveOSDashboardProps) {
  const [typedQuery, setTypedQuery] = useState('');
  const fullQueryText = queryText;

  // Typing effect for the raw query in Step 1
  useEffect(() => {
    if (stepId === 1) {
      const charCount = Math.floor((progress / 100) * fullQueryText.length);
      setTypedQuery(fullQueryText.slice(0, charCount));
    } else if (stepId > 1) {
      setTypedQuery(fullQueryText);
    } else {
      setTypedQuery('');
    }
  }, [stepId, progress, fullQueryText]);

  return (
    <div className="relative w-full max-w-5xl mx-auto space-y-6 select-none bg-slate-950/20 p-2 rounded-2xl border border-slate-900/40">
      
      {/* 1. QUERY PIPELINE SECTION (TOP) */}
      <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-4 shadow-xl relative overflow-hidden">
        {/* Glow corner */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-sky-500/5 rounded-full blur-xl pointer-events-none" />
        
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          {/* Query Input Box */}
          <div className="md:col-span-6 space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
              <Terminal className="w-3.5 h-3.5 text-sky-400" />
              <span>RAW_USER_QUERY_STREAM</span>
            </div>
            <div className="bg-slate-900/90 border border-slate-850 p-3 rounded-lg font-mono text-xs text-slate-200 min-h-[44px] flex items-center shadow-inner">
              <span className="text-sky-400 mr-2 font-bold">&gt;</span>
              <span>{typedQuery}</span>
              {stepId === 1 && progress < 99 && (
                <span className="w-1.5 h-4 bg-sky-400 animate-pulse ml-0.5" />
              )}
            </div>
          </div>

          {/* Tokens Box */}
          <div className="md:col-span-6 space-y-2">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
              <span>STRUCTURED_TOKEN_EXTRACTOR</span>
              {stepId >= 2 && (
                <span className="text-emerald-400 font-bold animate-pulse text-[8px] bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.2 rounded">
                  EXTRACTION_COMPLETE
                </span>
              )}
            </div>
            <div className="bg-slate-900/40 border border-slate-900/60 p-2.5 rounded-lg flex flex-wrap gap-2 items-center min-h-[44px] justify-start md:justify-center">
              {stepId >= 2 ? (
                tokens.map((tok, idx) => (
                  <div 
                    key={idx} 
                    className="animate-[scaleIn_0.3s_ease-out_both]"
                    style={{ animationDelay: `${idx * 150}ms` }}
                  >
                    <DataPacket label={tok} />
                  </div>
                ))
              ) : (
                <span className="text-slate-650 font-mono text-[10px] animate-pulse">Awaiting token matrix...</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SVG CONNECTIONS & PACKETS LAYER */}
      <div className="relative min-h-[360px] w-full flex flex-col justify-between">
        
        {/* Underlay SVG router paths */}
        <PacketRouter stepId={stepId} progress={progress} tokens={tokens} />

        {/* 2. AGENT GRID LAYER (MIDDLE) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10 w-full mt-2">
          <LiveOSAgentCard type="seasonality" stepId={stepId} progress={progress} commodity={analysisResult.parsed.commodity} />
          <LiveOSAgentCard type="arrival" stepId={stepId} progress={progress} commodity={analysisResult.parsed.commodity} />
          <LiveOSAgentCard type="external" stepId={stepId} progress={progress} commodity={analysisResult.parsed.commodity} />
        </div>

        {/* 3. FUSION CHAMBER / OUTPUT LAYER (BOTTOM/CENTER) */}
        <div className="relative z-10 w-full mt-8 min-h-[200px] flex items-center justify-center">
          
          {/* Standby/Idle state */}
          {stepId < 6 && (
            <div className="border border-slate-900/60 bg-slate-950/40 rounded-xl p-6 text-center max-w-sm w-full mx-auto flex flex-col items-center justify-center space-y-3 shadow-inner">
              <div className="w-10 h-10 rounded-full border border-slate-800 flex items-center justify-center bg-slate-900 relative">
                <Layers className="w-5 h-5 text-slate-700" />
                <div className="absolute inset-0 rounded-full border border-sky-400/5 animate-pulse" />
              </div>
              <div>
                <h5 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider">Fusion Chamber Inactive</h5>
                <p className="text-[9px] text-slate-600 font-mono mt-1">AWAITING_AGENT_TENSOR_SIGNALS</p>
              </div>
            </div>
          )}

          {/* Step 6: Meta Fusion Phase */}
          {stepId === 6 && (
            <div className="w-full">
              {progress < 40 ? (
                <div className="border border-slate-900 bg-slate-950/40 rounded-xl p-6 text-center max-w-sm w-full mx-auto flex flex-col items-center justify-center space-y-3">
                  <div className="w-10 h-10 rounded-full border border-sky-500/20 flex items-center justify-center bg-sky-950/20 relative animate-pulse">
                    <Layers className="w-5 h-5 text-sky-400 animate-spin" />
                  </div>
                  <div>
                    <h5 className="text-xs font-bold text-sky-400 font-mono uppercase tracking-wider">Receiving Agent Signals</h5>
                    <p className="text-[9px] text-sky-500/60 font-mono mt-1">STREAMING_TENSOR_OUTPUTS</p>
                  </div>
                </div>
              ) : progress < 75 ? (
                <div className="relative w-full h-40">
                  <FusionOrbit progress={progress} />
                </div>
              ) : (
                /* Step 6 post-collapse DNA attributions dashboard */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl px-4 mx-auto animate-[fadeInUp_500ms_ease-out_both]">
                  <div className="border border-slate-900 bg-slate-950/80 p-4 rounded-xl flex flex-col items-center shadow-lg relative">
                    <div className="absolute top-2 left-3 text-[9px] font-mono text-slate-500">DNA_ATTRIBUTION_CONTOUR</div>
                    <DecisionDNAChart progress={progress} dna={analysisResult.dna} />
                  </div>
                  <div className="space-y-4">
                    <div className="border border-slate-900 bg-slate-950/80 p-4 rounded-xl shadow-lg relative">
                      <div className="absolute top-2 left-3 text-[9px] font-mono text-slate-500">SIGNAL_STRENGTH_LED</div>
                      <DecisionScoreAnimator progress={progress} confidence={analysisResult.confidence} />
                    </div>
                    <div className="border border-slate-900 bg-slate-950/80 p-4 rounded-xl shadow-lg relative">
                      <div className="absolute top-2 left-3 text-[9px] font-mono text-slate-500">INFLUENCE_WEIGHTS_RANKING</div>
                      <InfluenceRanking details={analysisResult.details} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 7: Decision Engine builder */}
          {stepId === 7 && (
            <div className="w-full max-w-md mx-auto border border-slate-900 bg-slate-950/90 rounded-xl p-5 shadow-2xl animate-[fadeInUp_450ms_ease-out_both]">
              <DecisionBuilder progress={progress} details={analysisResult.details} confidence={analysisResult.confidence} />
            </div>
          )}

          {/* Step 8: Premium Forecast Result Card */}
          {stepId === 8 && (
            <div className="flex flex-col items-center justify-center space-y-4 animate-[fadeInUp_500ms_ease-out_both] w-full max-w-lg mx-auto">
              <span className="text-xs font-bold text-rose-450 uppercase tracking-widest bg-rose-950/40 border border-rose-500/20 px-3.5 py-1 rounded-full flex items-center gap-1.5 shadow-[0_0_15px_rgba(244,63,94,0.1)]">
                <CheckCircle2 className="w-4 h-4 text-rose-455" />
                SIMULATION PROCESS COMPLETED
              </span>

              <div className="w-full max-w-sm mt-2">
                <AnimatedCard 
                  glowColor={analysisResult.expectedChange.startsWith("-") ? "bearish" : "bullish"} 
                  className={`p-6 border-2 bg-slate-950/5 shadow-3xl ${
                    analysisResult.expectedChange.startsWith("-") 
                      ? "border-rose-500/30 shadow-[0_0_20px_rgba(244,63,94,0.1)]" 
                      : "border-emerald-500/30 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                  }`}
                >
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shadow-md ${
                        analysisResult.expectedChange.startsWith("-")
                          ? "bg-rose-950/50 border-rose-500 text-rose-450"
                          : "bg-emerald-950/50 border-emerald-500 text-emerald-450"
                      }`}>
                        <Compass className={`w-5 h-5 animate-[spin_8s_linear_infinite]`} />
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-100 text-base">{analysisResult.parsed.commodity}</h3>
                        <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold font-mono">
                          {analysisResult.parsed.market} Market
                        </p>
                      </div>
                    </div>
                    <span className={`text-[10px] font-bold border px-2.5 py-0.5 rounded-full uppercase tracking-wider font-mono animate-pulse ${
                      analysisResult.expectedChange.startsWith("-")
                        ? "text-rose-400 bg-rose-500/10 border-rose-500/20"
                        : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                    }`}>
                      {analysisResult.recommendation}
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-900">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">Expected Change</span>
                        <span className={`text-2xl font-bold mt-1 block ${
                          analysisResult.expectedChange.startsWith("-") ? "text-rose-450" : "text-emerald-450"
                        }`}>
                          {analysisResult.expectedChange}
                        </span>
                        <span className="text-[9px] text-slate-500 mt-0.5 block">Next 7 Days Trend</span>
                      </div>

                      <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-900">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">Confidence</span>
                        <span className="text-2xl font-bold text-sky-455 mt-1 block">
                          {analysisResult.confidence}%
                        </span>
                        <span className="text-[9px] text-slate-500 mt-0.5 block">Consensus Score</span>
                      </div>
                    </div>

                    <div className="border border-slate-900/50 bg-slate-950 p-3.5 rounded-lg">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-2 font-mono">
                        Decision DNA Summary
                      </span>
                      <div className="space-y-1.5 font-mono text-[10px] text-slate-400">
                        {analysisResult.details.map((item, idx) => (
                          <div key={idx} className="flex justify-between">
                            <span>{item.label}:</span>
                            <span className={item.impact.startsWith("-") ? "text-rose-400" : "text-emerald-400"}>
                              {item.impact}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </AnimatedCard>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* 4. EXECUTION TIMELINE TERMINAL (BOTTOM) */}
      <ExecutionTimeline stepId={stepId} progress={progress} />

    </div>
  );
}
