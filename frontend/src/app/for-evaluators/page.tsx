'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Compass, GraduationCap, Play, Pause, RotateCcw, FastForward, ShieldAlert } from 'lucide-react';
import { workflowSteps, WorkflowStepId } from '@/evaluator_demo/workflowConfig';
import LiveOSDashboard from '@/evaluator_demo/components/LiveOSDashboard';
import NarrationPanel from '@/evaluator_demo/components/NarrationPanel';
import EvaluationHighlights from '@/evaluator_demo/components/EvaluationHighlights';
import VivaQuestionsDrawer from '@/evaluator_demo/components/VivaQuestionsDrawer';
import EvaluationSummaryScreen from '@/evaluator_demo/components/EvaluationSummaryScreen';

import QueryInputPanel from '@/evaluator_demo/components/QueryInputPanel';
import QueryParserAnimation from '@/evaluator_demo/components/QueryParserAnimation';
import RecentQueries from '@/evaluator_demo/components/RecentQueries';
import { getMockAnalysis } from '@/evaluator_demo/components/MockAnalysisProvider';

export default function ForEvaluatorsPage() {
  const [currentStepId, setCurrentStepId] = useState<WorkflowStepId>(1);
  const [isSimulating, setIsSimulating] = useState(true); // Auto-play by default on mount!
  const [stepProgress, setStepProgress] = useState(0);
  const [simulationSpeed, setSimulationSpeed] = useState<number>(1);
  const [isVivaDrawerOpen, setIsVivaDrawerOpen] = useState(false);

  // Playground states
  const [queryText, setQueryText] = useState("Can I sell 5 tons of tomato in Kolar today?");
  const [demoMode, setDemoMode] = useState(true);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);

  // Load history from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("mandi_recent_queries");
    if (stored) {
      try {
        setRecentQueries(JSON.parse(stored));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const addRecentQuery = (q: string) => {
    setRecentQueries(prev => {
      const filtered = prev.filter(item => item !== q);
      const next = [q, ...filtered].slice(0, 10);
      localStorage.setItem("mandi_recent_queries", JSON.stringify(next));
      return next;
    });
  };

  const handleRunAnalysis = (inputText: string) => {
    setQueryText(inputText);
    addRecentQuery(inputText);
    setCurrentStepId(1);
    setStepProgress(0);
    elapsedRef.current = 0;
    setIsSimulating(true);
  };

  const handleResetQuery = () => {
    setQueryText("Can I sell 5 tons of tomato in Kolar today?");
    handleReset();
  };

  const analysisResult = getMockAnalysis(queryText);

  // Delta-time animation loop refs
  const elapsedRef = useRef(0);
  const requestRef = useRef<number | null>(null);

  const currentStepIdRef = useRef(currentStepId);
  const isSimulatingRef = useRef(isSimulating);
  const simulationSpeedRef = useRef(simulationSpeed);

  // Keep refs in sync with state
  useEffect(() => {
    currentStepIdRef.current = currentStepId;
  }, [currentStepId]);

  useEffect(() => {
    isSimulatingRef.current = isSimulating;
  }, [isSimulating]);

  useEffect(() => {
    simulationSpeedRef.current = simulationSpeed;
  }, [simulationSpeed]);

  // Robust delta-time requestAnimationFrame loop
  useEffect(() => {
    let lastTime = performance.now();

    const loop = (time: number) => {
      const delta = time - lastTime;
      lastTime = time;

      if (isSimulatingRef.current) {
        const stepId = currentStepIdRef.current;
        const speed = simulationSpeedRef.current;
        const stepConfig = workflowSteps.find(s => s.id === stepId);

        if (stepConfig) {
          const stepDuration = stepConfig.duration / speed;
          elapsedRef.current += delta;
          const progressPercent = Math.min((elapsedRef.current / stepDuration) * 100, 100);

          setStepProgress(progressPercent);

          if (elapsedRef.current >= stepDuration) {
            elapsedRef.current = 0;
            if (stepId < 8) {
              setCurrentStepId((stepId + 1) as WorkflowStepId);
              setStepProgress(0);
            } else {
              setIsSimulating(false);
            }
          }
        }
      }

      requestRef.current = requestAnimationFrame(loop);
    };

    requestRef.current = requestAnimationFrame(loop);

    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, []);

  const handleStart = () => {
    if (currentStepId === 8) {
      setCurrentStepId(1);
      setStepProgress(0);
      elapsedRef.current = 0;
    }
    setIsSimulating(true);
  };

  const handlePause = () => {
    setIsSimulating(false);
  };

  const handleReset = () => {
    setIsSimulating(false);
    setCurrentStepId(1);
    setStepProgress(0);
    elapsedRef.current = 0;
  };

  const handleSpeedToggle = () => {
    setSimulationSpeed(speed => {
      if (speed === 1) return 2;
      if (speed === 2) return 0.5;
      return 1;
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden font-sans">
      
      {/* Background grids */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#48d0ff_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)] bg-[size:100px_100px]" />
      
      {/* Glowing background details */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-sky-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />

      {/* Workspace */}
      <div className="container mx-auto px-4 py-8 flex-1 flex flex-col justify-start relative z-10">
        
        {/* Header */}
        <header className="mb-6 border-b border-slate-900 pb-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-400/20 uppercase font-mono animate-pulse">
                <GraduationCap className="w-3.5 h-3.5" />
                Guided Evaluation Mode
              </span>
              <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-400/20 uppercase font-mono">
                Self-Explaining AI
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100">
              MandiSense Observability Hub
            </h1>
            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              This guided demonstration utilizes real-time explainability narration, contribution attributions, and technical model telemetry to present pipeline diagnostics.
            </p>
          </div>

          <div className="flex items-center gap-3 bg-slate-950/60 border border-slate-900 px-4 py-2.5 rounded-lg text-slate-500 text-xs font-mono">
            <ShieldAlert className="w-4 h-4 text-emerald-500 animate-pulse" />
            <span>AUTO_RUNNING: PRESENTATION_ACTIVE</span>
          </div>
        </header>

        {/* Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* LEFT COLUMN: Controls, LiveOS Dashboard, Decision Flowchart (8 Cols) */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* Query Input Panel */}
            <QueryInputPanel
              onRun={handleRunAnalysis}
              onReset={handleResetQuery}
              demoMode={demoMode}
              onToggleDemoMode={setDemoMode}
              isSimulating={isSimulating && currentStepId > 1 && currentStepId < 8}
            />

            {/* Playback Controls */}
            <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-lg">
              <div className="flex items-center gap-3">
                {!isSimulating ? (
                  <button
                    onClick={handleStart}
                    className="py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wide transition-all shadow-[0_0_12px_rgba(16,185,129,0.2)] flex items-center gap-1.5 active:scale-[0.98]"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    {currentStepId === 8 ? 'Re-Run Simulation' : 'Resume Narration'}
                  </button>
                ) : (
                  <button
                    onClick={handlePause}
                    className="py-2 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs tracking-wide transition-all shadow-[0_0_12px_rgba(245,158,11,0.2)] flex items-center gap-1.5 active:scale-[0.98]"
                  >
                    <Pause className="w-3.5 h-3.5 fill-current" />
                    Pause Narration
                  </button>
                )}

                <button
                  onClick={handleResetQuery}
                  className="py-2 px-3.5 rounded-lg border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-slate-200 font-semibold text-xs transition-all flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </button>

                <button
                  onClick={handleSpeedToggle}
                  className="py-2 px-3.5 rounded-lg border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-slate-200 font-semibold text-xs transition-all flex items-center gap-1.5"
                >
                  <FastForward className="w-3.5 h-3.5" />
                  Speed: {simulationSpeed}x
                </button>
              </div>

              <div className="flex items-center gap-2 font-mono text-[10px] text-slate-500">
                <span>SIMULATION_PROGRESS:</span>
                <span className="text-sky-400 font-bold">{Math.floor(stepProgress)}%</span>
              </div>
            </div>

            {/* Query Parser Animation View (During Step 1 & 2 only) */}
            {(currentStepId === 1 || currentStepId === 2) && (
              <div className="animate-[fadeInUp_400ms_ease-out_both]">
                <QueryParserAnimation
                  progress={stepProgress + (currentStepId === 2 ? 100 : 0)}
                  parsed={analysisResult.parsed}
                  queryText={queryText}
                />
              </div>
            )}

            {/* Dashboard viewport */}
            <LiveOSDashboard
              stepId={currentStepId}
              progress={stepProgress}
              queryText={queryText}
              tokens={analysisResult.parsed.tokens}
              analysisResult={analysisResult}
            />

            {/* Replay button when finished */}
            {currentStepId === 8 && (
              <div className="flex justify-center animate-[fadeInUp_500ms_ease-out_both]">
                <button
                  onClick={() => handleRunAnalysis(queryText)}
                  className="w-full max-w-sm py-3 px-6 rounded-xl border border-sky-500/30 bg-sky-950/20 hover:bg-sky-950/40 text-sky-400 font-extrabold text-xs tracking-wider uppercase font-mono transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(56,189,248,0.05)] active:scale-[0.98]"
                >
                  <RotateCcw className="w-4 h-4 text-sky-455" />
                  Replay Analysis
                </button>
              </div>
            )}

            {/* Decision Flowchart appears below when completed */}
            {currentStepId === 8 && (
              <div className="animate-[fadeInUp_600ms_ease-out_both]">
                <EvaluationSummaryScreen />
              </div>
            )}

          </div>

          {/* RIGHT COLUMN: Auto Narration & Highlights (4 Cols) */}
          <div className="lg:col-span-4 space-y-6">
            
            {/* Auto Narration Panel */}
            <NarrationPanel 
              stepId={currentStepId} 
              progress={stepProgress}
              onOpenQuestions={() => setIsVivaDrawerOpen(true)}
            />

            {/* Checklist Highlights */}
            <EvaluationHighlights 
              stepId={currentStepId} 
              progress={stepProgress}
            />

            {/* History of Recent Queries */}
            <RecentQueries
              queries={recentQueries}
              onClickQuery={handleRunAnalysis}
              isSimulating={isSimulating && currentStepId > 1 && currentStepId < 8}
            />

          </div>

        </div>

      </div>

      {/* Slide-out Viva Questions Drawer */}
      <VivaQuestionsDrawer 
        isOpen={isVivaDrawerOpen} 
        onClose={() => setIsVivaDrawerOpen(false)} 
        stepId={currentStepId}
      />

    </div>
  );
}
