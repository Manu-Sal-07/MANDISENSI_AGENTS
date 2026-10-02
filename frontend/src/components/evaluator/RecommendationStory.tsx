'use client';

import React, { useState, useEffect } from 'react';
import { Play, CheckCircle, Sparkles, Layers, Activity, Info } from 'lucide-react';

interface RecommendationStoryProps {
  stepOverride?: number;
}

export default function RecommendationStory({ stepOverride }: RecommendationStoryProps) {
  const [step, setStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [animationId, setAnimationId] = useState<number>(0);

  // Determine if controlled externally
  const isControlled = stepOverride !== undefined;
  const effectiveStep = isControlled ? stepOverride : step;

  // Sequenced animation controller (only runs if not controlled externally)
  useEffect(() => {
    if (isControlled || !isPlaying) return;

    const timings = [
      { step: 1, delay: 1500 }, // Seasonality Agent active & particle runs
      { step: 2, delay: 1500 }, // Arrival Agent active & particle runs
      { step: 3, delay: 1500 }, // External Agent active & particle runs
      { step: 4, delay: 2200 }, // Meta Ensemble active, checkmarks load
      { step: 5, delay: 1500 }, // Decision Engine active & particle runs
      { step: 6, delay: 0 },    // Reveal card & Explainability Panel
    ];

    let currentTimeout: NodeJS.Timeout;

    const runStep = (idx: number) => {
      if (idx >= timings.length) {
        setIsPlaying(false);
        return;
      }

      setStep(timings[idx].step);

      if (timings[idx].delay > 0) {
        currentTimeout = setTimeout(() => {
          runStep(idx + 1);
        }, timings[idx].delay);
      } else {
        setIsPlaying(false);
      }
    };

    runStep(0);

    return () => {
      if (currentTimeout) clearTimeout(currentTimeout);
    };
  }, [isPlaying, animationId, isControlled]);

  const handleStart = () => {
    if (isControlled) return;
    setStep(0);
    setAnimationId(prev => prev + 1);
    setIsPlaying(true);
  };

  const handleReset = () => {
    if (isControlled) return;
    setIsPlaying(false);
    setStep(0);
  };

  // Helper styles based on step active state
  const getAgentCardClass = (activeStep: number) => {
    if (effectiveStep === 0) return 'opacity-30 border-slate-900 bg-slate-950/10 scale-100';
    if (effectiveStep === activeStep) return 'border-emerald-500 bg-emerald-950/20 shadow-[0_0_20px_rgba(16,185,129,0.15)] scale-[1.02] duration-300 z-10';
    if (effectiveStep > activeStep) return 'border-slate-800 bg-slate-950/40 opacity-70';
    return 'opacity-20 scale-[0.98] border-slate-900/50';
  };

  return (
    <div className="w-full bg-[#09101d]/90 backdrop-blur-xl border border-slate-900/80 rounded-[2.5rem] p-6 md:p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative overflow-hidden">
      {/* Background radial accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full blur-[140px] pointer-events-none opacity-25 bg-emerald-500/5" />

      {/* Header controls area */}
      <div className="relative z-10 border-b border-slate-900 pb-5 mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1 text-[9px] font-mono font-bold tracking-[0.2em] text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 uppercase animate-pulse">
              <Sparkles className="w-3.5 h-3.5" />
              Decision Storyboard
            </span>
          </div>
          <h3 className="text-lg font-black text-slate-100 tracking-tight">
            Recommendation Generation Story
          </h3>
          <p className="text-xs text-slate-450 leading-relaxed max-w-xl font-sans mt-0.5">
            Watch how the system aggregates predictions, weights agent outputs, resolves conflicts, and dispatches the final hold recommendation.
          </p>
        </div>

        {/* Buttons controls (Only show if not controlled externally) */}
        {!isControlled && (
          <div className="flex gap-3">
            <button
              onClick={handleStart}
              disabled={isPlaying}
              className="py-3 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wider uppercase transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)] flex items-center gap-2 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {step === 6 ? 'Re-play Story' : 'Generate Recommendation'}
            </button>
            
            <button
              onClick={handleReset}
              disabled={step === 0}
              className="py-3 px-4 rounded-xl border border-slate-900 bg-slate-950/40 hover:bg-slate-900 text-slate-500 hover:text-slate-300 font-semibold text-xs tracking-wider uppercase transition-all disabled:opacity-10"
            >
              Reset
            </button>
          </div>
        )}
      </div>

      {/* HORIZONTAL LEFT-TO-RIGHT EVIDENCE FLOW GRID */}
      <div className="relative z-10 flex flex-col lg:flex-row items-stretch justify-between gap-0 min-h-[350px]">
        
        {/* COLUMN 1: AGENTS (3 Cards stack) */}
        <div className="flex flex-col justify-between h-[330px] w-full lg:w-64 z-10 shrink-0 gap-4">
          
          {/* Agent A: Seasonality */}
          <div className={`border rounded-2xl p-3.5 transition-all duration-500 ${getAgentCardClass(1)}`}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] font-bold text-slate-200 tracking-tight block">Seasonality Agent</span>
              {effectiveStep >= 1 && <span className="text-[9px] font-mono text-emerald-400 font-black">+4.2%</span>}
            </div>
            <p className="text-[11px] text-slate-400 leading-snug font-sans">
              Strong seasonal uptrend validated by historic holiday price spikes.
            </p>
            <div className="flex justify-between items-center mt-2.5 text-[9px] font-mono text-slate-550 border-t border-slate-900/60 pt-1.5">
              <span>Confidence: 92%</span>
              <span>W: 38%</span>
            </div>
          </div>

          {/* Agent B: Arrival */}
          <div className={`border rounded-2xl p-3.5 transition-all duration-500 ${getAgentCardClass(2)}`}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] font-bold text-slate-200 tracking-tight block">Arrival Agent</span>
              {effectiveStep >= 2 && <span className="text-[9px] font-mono text-emerald-400 font-black">+5.1%</span>}
            </div>
            <p className="text-[11px] text-slate-400 leading-snug font-sans">
              Supply stress detected with regional inflows contracting at Kolar.
            </p>
            <div className="flex justify-between items-center mt-2.5 text-[9px] font-mono text-slate-550 border-t border-slate-900/60 pt-1.5">
              <span>Confidence: 89%</span>
              <span>W: 47%</span>
            </div>
          </div>

          {/* Agent C: External Factors */}
          <div className={`border rounded-2xl p-3.5 transition-all duration-500 ${getAgentCardClass(3)}`}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px] font-bold text-slate-200 tracking-tight block">External Agent</span>
              {effectiveStep >= 3 && <span className="text-[9px] font-mono text-violet-400 font-black">-0.7%</span>}
            </div>
            <p className="text-[11px] text-slate-400 leading-snug font-sans">
              Weather uncertainty and logistics fuel surcharges buffer price spikes.
            </p>
            <div className="flex justify-between items-center mt-2.5 text-[9px] font-mono text-slate-550 border-t border-slate-900/60 pt-1.5">
              <span>Confidence: 90%</span>
              <span>W: 15%</span>
            </div>
          </div>

        </div>

        {/* CONNECTOR 1: Agents to Meta Ensemble */}
        <div className="hidden lg:block w-20 relative self-stretch z-0">
          <svg className="absolute inset-0 w-full h-full" key={`conn1-${animationId}-${effectiveStep}`}>
            {/* Background static paths */}
            <path d="M 0 50 Q 40 50 40 165 L 80 165" fill="none" stroke="#1e293b" strokeWidth="1.5" />
            <path d="M 0 165 L 80 165" fill="none" stroke="#1e293b" strokeWidth="1.5" />
            <path d="M 0 280 Q 40 280 40 165 L 80 165" fill="none" stroke="#1e293b" strokeWidth="1.5" />

            {/* Glowing flowing dash paths when active */}
            {effectiveStep >= 1 && (
              <path d="M 0 50 Q 40 50 40 165 L 80 165" fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4,4" className="animate-[dash_2s_infinite_linear]" />
            )}
            {effectiveStep >= 2 && (
              <path d="M 0 165 L 80 165" fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4,4" className="animate-[dash_2s_infinite_linear]" />
            )}
            {effectiveStep >= 3 && (
              <path d="M 0 280 Q 40 280 40 165 L 80 165" fill="none" stroke="#8b5cf6" strokeWidth="1.5" strokeDasharray="4,4" className="animate-[dash_2s_infinite_linear]" />
            )}

            {/* Moving glowing particles */}
            {!isControlled && isPlaying && effectiveStep === 1 && (
              <circle r="4.5" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}>
                <animateMotion dur="1s" repeatCount="1" path="M 0 50 Q 40 50 40 165 L 80 165" fill="freeze" />
              </circle>
            )}
            {!isControlled && isPlaying && effectiveStep === 2 && (
              <circle r="4.5" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}>
                <animateMotion dur="1s" repeatCount="1" path="M 0 165 L 80 165" fill="freeze" />
              </circle>
            )}
            {!isControlled && isPlaying && effectiveStep === 3 && (
              <circle r="4.5" fill="#8b5cf6" style={{ filter: 'drop-shadow(0 0 6px #8b5cf6)' }}>
                <animateMotion dur="1s" repeatCount="1" path="M 0 280 Q 40 280 40 165 L 80 165" fill="freeze" />
              </circle>
            )}

            {/* Controlled constant streaming particles when at specific states */}
            {isControlled && effectiveStep === 1 && (
              <circle r="4.5" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}>
                <animateMotion dur="1.2s" repeatCount="indefinite" path="M 0 50 Q 40 50 40 165 L 80 165" />
              </circle>
            )}
            {isControlled && effectiveStep === 2 && (
              <circle r="4.5" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}>
                <animateMotion dur="1.2s" repeatCount="indefinite" path="M 0 165 L 80 165" />
              </circle>
            )}
            {isControlled && effectiveStep === 3 && (
              <circle r="4.5" fill="#8b5cf6" style={{ filter: 'drop-shadow(0 0 6px #8b5cf6)' }}>
                <animateMotion dur="1.2s" repeatCount="indefinite" path="M 0 280 Q 40 280 40 165 L 80 165" />
              </circle>
            )}
          </svg>
          
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes dash {
              to {
                stroke-dashoffset: -20;
              }
            }
          `}} />
        </div>

        {/* COLUMN 2: META ENSEMBLE PANEL */}
        <div className={`w-full lg:w-60 self-center border rounded-[2rem] p-5 transition-all duration-500 shrink-0 ${
          effectiveStep === 0 ? 'opacity-30 border-slate-900 bg-slate-950/10' :
          effectiveStep === 4 ? 'border-indigo-500 bg-indigo-950/20 shadow-[0_0_20px_rgba(99,102,241,0.2)] scale-[1.01] z-10' :
          effectiveStep > 4 ? 'border-slate-800 bg-slate-950/40 opacity-90' : 'opacity-20 scale-[0.98]'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span className="text-[10px] font-black text-slate-200 tracking-tight">Meta Ensemble</span>
          </div>

          {/* Fusion details */}
          <div className="space-y-3 font-mono text-[10px]">
            {/* Weights info */}
            <div className="bg-slate-950/60 border border-slate-900 rounded-xl p-2.5 space-y-1.5 text-slate-450">
              <div className="flex justify-between">
                <span>Seasonality W:</span>
                <span className={effectiveStep >= 4 ? 'text-indigo-300 font-bold' : ''}>38%</span>
              </div>
              <div className="flex justify-between">
                <span>Arrival W:</span>
                <span className={effectiveStep >= 4 ? 'text-indigo-300 font-bold' : ''}>47%</span>
              </div>
              <div className="flex justify-between">
                <span>External W:</span>
                <span className={effectiveStep >= 4 ? 'text-indigo-300 font-bold' : ''}>15%</span>
              </div>
            </div>

            {/* Fusion steps checklists */}
            <div className="space-y-2 pt-2 border-t border-slate-900">
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${effectiveStep >= 4 ? 'bg-indigo-400 animate-ping' : 'bg-slate-800'}`} />
                <span className={effectiveStep >= 4 ? 'text-slate-300 font-bold' : 'text-slate-600'}>Weighted Fusion</span>
                {effectiveStep >= 4 && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 ml-auto" />}
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${effectiveStep >= 4 ? 'bg-indigo-400' : 'bg-slate-800'}`} />
                <span className={effectiveStep >= 4 ? 'text-slate-300 font-bold' : 'text-slate-600'}>Confidence Fusion</span>
                {effectiveStep >= 4 && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 ml-auto" />}
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${effectiveStep >= 4 ? 'bg-indigo-400' : 'bg-slate-800'}`} />
                <span className={effectiveStep >= 4 ? 'text-slate-300 font-bold' : 'text-slate-600'}>Conflict Resolution</span>
                {effectiveStep >= 4 && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 ml-auto" />}
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${effectiveStep >= 4 ? 'bg-indigo-400' : 'bg-slate-800'}`} />
                <span className={effectiveStep >= 4 ? 'text-slate-300 font-bold' : 'text-slate-600'}>Risk Assessment</span>
                {effectiveStep >= 4 && <CheckCircle className="w-3.5 h-3.5 text-emerald-400 ml-auto" />}
              </div>
            </div>
          </div>
        </div>

        {/* CONNECTOR 2: Ensemble to Decision Engine */}
        <div className="hidden lg:block w-14 relative self-stretch z-0">
          <svg className="absolute inset-0 w-full h-full" key={`conn2-${animationId}-${effectiveStep}`}>
            <path d="M 0 165 L 56 165" fill="none" stroke="#1e293b" strokeWidth="1.5" />
            {effectiveStep >= 4 && (
              <path d="M 0 165 L 56 165" fill="none" stroke="#6366f1" strokeWidth="1.5" strokeDasharray="4,4" className="animate-[dash_2s_infinite_linear]" />
            )}
            {!isControlled && isPlaying && effectiveStep === 4 && (
              <circle r="4.5" fill="#818cf8" style={{ filter: 'drop-shadow(0 0 6px #818cf8)' }}>
                <animateMotion dur="1s" repeatCount="1" path="M 0 165 L 56 165" fill="freeze" />
              </circle>
            )}
            {isControlled && effectiveStep === 4 && (
              <circle r="4.5" fill="#818cf8" style={{ filter: 'drop-shadow(0 0 6px #818cf8)' }}>
                <animateMotion dur="1.2s" repeatCount="indefinite" path="M 0 165 L 56 165" />
              </circle>
            )}
          </svg>
        </div>

        {/* COLUMN 3: DECISION ENGINE */}
        <div className={`w-full lg:w-44 self-center border rounded-[2rem] p-5 transition-all duration-500 shrink-0 text-center ${
          effectiveStep === 0 ? 'opacity-30 border-slate-900 bg-slate-950/10' :
          effectiveStep === 5 ? 'border-cyan-500 bg-cyan-950/20 shadow-[0_0_20px_rgba(6,182,212,0.2)] scale-[1.01] z-10' :
          effectiveStep > 5 ? 'border-slate-800 bg-slate-950/40 opacity-90' : 'opacity-20 scale-[0.98]'
        }`}>
          <div className="flex items-center justify-center gap-1.5 mb-3">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] font-black text-slate-200 tracking-tight">Decision Engine</span>
          </div>

          <div className="space-y-3.5 font-mono">
            <div>
              <span className="block text-[8px] text-slate-500 uppercase tracking-widest leading-none mb-1">Fused Forecast</span>
              <span className={`text-base font-black ${effectiveStep >= 5 ? 'text-cyan-400' : 'text-slate-650'}`}>+4.7% Trend</span>
            </div>
            <div>
              <span className="block text-[8px] text-slate-500 uppercase tracking-widest leading-none mb-1">Combined Trust</span>
              <span className={`text-base font-black ${effectiveStep >= 5 ? 'text-emerald-400' : 'text-slate-650'}`}>84% Conf</span>
            </div>
          </div>
        </div>

        {/* CONNECTOR 3: Decision Engine to Final Recommendation */}
        <div className="hidden lg:block w-14 relative self-stretch z-0">
          <svg className="absolute inset-0 w-full h-full" key={`conn3-${animationId}-${effectiveStep}`}>
            <path d="M 0 165 L 56 165" fill="none" stroke="#1e293b" strokeWidth="1.5" />
            {effectiveStep >= 5 && (
              <path d="M 0 165 L 56 165" fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4,4" className="animate-[dash_2s_infinite_linear]" />
            )}
            {!isControlled && isPlaying && effectiveStep === 5 && (
              <circle r="4.5" fill="#10b981" style={{ filter: 'drop-shadow(0 0 6px #10b981)' }}>
                <animateMotion dur="1s" repeatCount="1" path="M 0 165 L 56 165" fill="freeze" />
              </circle>
            )}
            {isControlled && effectiveStep === 5 && (
              <circle r="4.5" fill="#10b981" style={{ filter: 'drop-shadow(0 0 6px #10b981)' }}>
                <animateMotion dur="1.2s" repeatCount="indefinite" path="M 0 165 L 56 165" />
              </circle>
            )}
          </svg>
        </div>

        {/* COLUMN 4: FINAL RECOMMENDATION CARD */}
        <div className="w-full lg:w-72 self-center shrink-0">
          {effectiveStep === 6 ? (
            <div className="bg-slate-950 border-2 border-emerald-500 rounded-[2rem] p-5 shadow-[0_0_30px_rgba(16,185,129,0.2)] relative overflow-hidden animate-[storyRevealCard_0.6s_ease-out_both]">
              <style dangerouslySetInnerHTML={{__html: `
                @keyframes storyRevealCard {
                  from { opacity: 0; transform: translateY(12px) scale(0.98); }
                  to { opacity: 1; transform: translateY(0) scale(1); }
                }
              `}} />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.05),transparent_60%)] pointer-events-none" />

              <div className="relative z-10 space-y-4 text-center">
                <div>
                  <span className="flex items-center justify-center gap-1.5 text-[8.5px] font-mono font-bold tracking-[0.2em] text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 uppercase w-max mx-auto">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    Final Recommendation
                  </span>
                </div>

                <div className="space-y-1">
                  <h4 className="text-base font-black text-slate-100 tracking-tight leading-none">HOLD TOMATO FOR 7 DAYS</h4>
                  <span className="text-[10px] text-slate-450 block font-sans">Decision triggered by dynamic regime fusion</span>
                </div>

                <div className="grid grid-cols-2 gap-3 border-t border-slate-900 pt-3">
                  <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-900 text-center">
                    <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest leading-none mb-1">Expected Gain</span>
                    <span className="text-xs font-black text-cyan-400">₹250/q</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-900 text-center">
                    <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest leading-none mb-1">Ensemble Conf</span>
                    <span className="text-xs font-black text-emerald-400">84%</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-950/20 border border-slate-900 border-dashed rounded-[2rem] p-6 text-center text-slate-550 flex flex-col items-center justify-center py-12 gap-3 min-h-[180px]">
              <Sparkles className="w-7 h-7 text-slate-700 animate-pulse" />
              <div>
                <h4 className="text-xs font-bold text-slate-450">Awaiting Story Synthesis</h4>
                <p className="text-[10.5px] text-slate-600 mt-1 max-w-[200px] leading-relaxed">
                  Trigger the recommendation story sequence to follow the evidence flow.
                </p>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* EXPLAINABILITY PANEL */}
      {effectiveStep === 6 && (
        <div className="relative z-10 mt-8 pt-6 border-t border-slate-900/80 space-y-4 animate-[fadeIn_0.5s_ease-out_both]">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-400" />
            <h4 className="text-xs font-black text-slate-100 uppercase tracking-wider">Explainability Panel // Reasoning Logs</h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            
            <div className="bg-slate-950/60 border border-slate-900/60 rounded-xl p-3 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200 block tracking-tight font-black">Seasonal Uptrend</strong>
                <span className="text-[10px] text-slate-450 mt-0.5 block font-sans">
                  Autoregressive and STL baseline models identify strong structural month-on-month tomato demand.
                </span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-900/60 rounded-xl p-3 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200 block tracking-tight font-black">Supply Tightening</strong>
                <span className="text-[10px] text-slate-450 mt-0.5 block font-sans">
                  Autoregressive inflow models validate severe volume stress at neighboring mandis (Kolar arrivals down by 5.1%).
                </span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-900/60 rounded-xl p-3 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200 block tracking-tight font-black">Stable Market Outlook</strong>
                <span className="text-[10px] text-slate-450 mt-0.5 block font-sans">
                  News Sentiment Classifier maps stable margins despite logistics surcharges and weather buffers.
                </span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-900/60 rounded-xl p-3 text-xs flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200 block tracking-tight font-black">High Confidence Agreement</strong>
                <span className="text-[10px] text-slate-450 mt-0.5 block font-sans">
                  Multi-agent consensus exceeds the $80\%$ execution threshold, validating the Hold tomato suggestion.
                </span>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
