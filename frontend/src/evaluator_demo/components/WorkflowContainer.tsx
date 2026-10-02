'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, FastForward, Activity } from 'lucide-react';
import StepIndicator from './StepIndicator';
import WorkflowStep from './WorkflowStep';
import { workflowSteps, WorkflowStepId } from '../workflowConfig';

export default function WorkflowContainer() {
  const [currentStepId, setCurrentStepId] = useState<WorkflowStepId | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [stepProgress, setStepProgress] = useState(0);
  const [simulationSpeed, setSimulationSpeed] = useState<number>(1); // 1x, 2x, 0.5x
  
  // Timer references
  const requestRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const elapsedBeforePauseRef = useRef<number>(0);

  // Handle run/start
  const handleStart = () => {
    if (currentStepId === null || currentStepId === 8) {
      // Start from step 1
      setCurrentStepId(1);
      setStepProgress(0);
      elapsedBeforePauseRef.current = 0;
    }
    setIsSimulating(true);
  };

  // Handle pause
  const handlePause = () => {
    setIsSimulating(false);
    if (requestRef.current) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    }
  };

  // Handle reset
  const handleReset = () => {
    setIsSimulating(false);
    if (requestRef.current) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    }
    setCurrentStepId(null);
    setStepProgress(0);
    elapsedBeforePauseRef.current = 0;
    startTimeRef.current = null;
  };

  // Handle speed change
  const handleSpeedToggle = () => {
    setSimulationSpeed(currentSpeed => {
      if (currentSpeed === 1) return 2;
      if (currentSpeed === 2) return 0.5;
      return 1;
    });
  };

  // Animation Loop Effect
  useEffect(() => {
    if (!isSimulating || currentStepId === null) {
      return;
    }

    const stepConfig = workflowSteps.find(s => s.id === currentStepId);
    if (!stepConfig) return;

    // Calculate total duration for this step adjusted for speed
    const stepDuration = stepConfig.duration / simulationSpeed;

    const animate = (time: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = time;
      }

      // Calculate how much time has passed since we started this step
      const elapsed = (time - startTimeRef.current) + elapsedBeforePauseRef.current;
      const progressPercent = Math.min((elapsed / stepDuration) * 100, 100);

      setStepProgress(progressPercent);

      if (elapsed >= stepDuration) {
        // Step finished!
        if (currentStepId < 8) {
          // Go to next step
          setCurrentStepId(prev => (prev ? (prev + 1) as WorkflowStepId : 1));
          setStepProgress(0);
          startTimeRef.current = null;
          elapsedBeforePauseRef.current = 0;
        } else {
          // Finished step 8, end simulation
          setIsSimulating(false);
          if (requestRef.current) {
            cancelAnimationFrame(requestRef.current);
            requestRef.current = null;
          }
        }
      } else {
        requestRef.current = requestAnimationFrame(animate);
      }
    };

    // Start the animation loop
    requestRef.current = requestAnimationFrame(animate);

    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      // Save elapsed time to support resuming properly
      if (startTimeRef.current) {
        const now = performance.now();
        elapsedBeforePauseRef.current += (now - startTimeRef.current);
        startTimeRef.current = null;
      }
    };
  }, [isSimulating, currentStepId, simulationSpeed]);

  const activeStepConfig = currentStepId 
    ? workflowSteps.find(s => s.id === currentStepId) 
    : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* LEFT COLUMN: Controls & Steps timeline */}
      <div className="lg:col-span-4 flex flex-col gap-6">
        
        {/* Core Simulation Controls */}
        <div className="border border-slate-800 bg-slate-950/80 rounded-xl p-5 shadow-[0_0_20px_rgba(0,0,0,0.4)] backdrop-blur-xl">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
            System Control Panel
          </h3>

          <div className="flex flex-col gap-3">
            {/* Primary Action Button */}
            {!isSimulating ? (
              <button
                onClick={handleStart}
                className="w-full py-3 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm tracking-wide transition-all shadow-[0_0_15px_rgba(16,185,129,0.25)] flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <Play className="w-4 h-4 fill-current" />
                {currentStepId === 8 ? 'Re-Run System' : currentStepId ? 'Resume Simulation' : 'Run System'}
              </button>
            ) : (
              <button
                onClick={handlePause}
                className="w-full py-3 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-sm tracking-wide transition-all shadow-[0_0_15px_rgba(245,158,11,0.25)] flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <Pause className="w-4 h-4 fill-current" />
                Pause Simulation
              </button>
            )}

            {/* Sub-controls */}
            <div className="grid grid-cols-2 gap-3 mt-1">
              <button
                onClick={handleReset}
                disabled={currentStepId === null}
                className="py-2.5 px-3 rounded-lg border border-slate-850 hover:bg-slate-900 text-slate-400 hover:text-slate-200 font-semibold text-xs transition-all flex items-center justify-center gap-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>

              <button
                onClick={handleSpeedToggle}
                className="py-2.5 px-3 rounded-lg border border-slate-850 hover:bg-slate-900 text-slate-400 hover:text-slate-200 font-semibold text-xs transition-all flex items-center justify-center gap-1.5"
              >
                <FastForward className="w-3.5 h-3.5" />
                Speed: {simulationSpeed}x
              </button>
            </div>
          </div>

          {/* Mini Status Monitor */}
          <div className="mt-5 border-t border-slate-900 pt-4 flex items-center justify-between font-mono text-[10px] text-slate-500">
            <span>ENGINE_STATE:</span>
            <span className={`font-bold ${
              isSimulating ? 'text-sky-400' : currentStepId ? 'text-amber-500' : 'text-slate-600'
            }`}>
              {isSimulating ? 'SIMULATING' : currentStepId ? 'PAUSED' : 'IDLE'}
            </span>
          </div>
        </div>

        {/* Vertical Pipeline Progress Steps */}
        <div className="border border-slate-800 bg-slate-950/80 rounded-xl p-5 shadow-[0_0_20px_rgba(0,0,0,0.4)] backdrop-blur-xl">
          <StepIndicator 
            steps={workflowSteps}
            currentStepId={currentStepId}
            currentProgress={stepProgress}
            isSimulating={isSimulating}
          />
        </div>

      </div>

      {/* RIGHT COLUMN: Operational Viewport display */}
      <div className="lg:col-span-8">
        <div className="border border-slate-800 bg-slate-950/60 rounded-xl overflow-hidden shadow-[0_0_25px_rgba(0,0,0,0.5)] backdrop-blur-xl">
          
          {/* Viewport Top Header bar */}
          <div className="bg-slate-900/95 border-b border-slate-800 px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isSimulating ? 'bg-sky-400' : 'bg-slate-500'
                }`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  isSimulating ? 'bg-sky-500' : 'bg-slate-500'
                }`} />
              </div>
              <span className="font-mono text-[10px] tracking-wider uppercase font-semibold text-slate-400">
                Operational Viewport
              </span>
            </div>
            {activeStepConfig && (
              <span className="text-[10px] font-mono text-slate-500">
                ACTIVE_STEP: {activeStepConfig.statusText}
              </span>
            )}
          </div>

          {/* Viewport Main Inner Display Area */}
          <div className="p-6 md:p-8 min-h-[400px] flex flex-col justify-between relative bg-[radial-gradient(circle_at_50%_40%,rgba(15,23,42,0.3),transparent_70%)]">
            
            {/* Ambient Hex / Grid Background */}
            <div className="absolute inset-0 opacity-5 pointer-events-none bg-[linear-gradient(rgba(148,163,184,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.05)_1px,transparent_1px)] bg-[size:20px_20px]" />

            {currentStepId ? (
              <div className="flex-1 flex flex-col justify-center">
                <WorkflowStep 
                  stepId={currentStepId} 
                  progress={stepProgress} 
                />
              </div>
            ) : (
              // Initial State / Waiting state
              <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6 py-12">
                <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center shadow-[0_0_20px_rgba(56,189,248,0.05)] relative group hover:border-sky-500/30 transition-all duration-300">
                  <Activity className="w-8 h-8 text-slate-600 group-hover:text-sky-400/80 transition-colors" />
                  <div className="absolute inset-0 rounded-full border border-sky-400/5 animate-pulse" />
                </div>
                <div className="max-w-md">
                  <h3 className="text-lg font-bold text-slate-200">Simulation Offline</h3>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    Click the <strong className="text-emerald-400">Run System</strong> button on the left to start the simulated multi-agent forecasting pipeline and observe step-by-step telemetry.
                  </p>
                </div>
              </div>
            )}

            {/* Viewport footer notes */}
            {activeStepConfig && (
              <div className="mt-6 pt-4 border-t border-slate-900/60 text-slate-500 text-[10px] font-mono flex flex-col md:flex-row md:justify-between gap-2">
                <span>STAGE: {activeStepConfig.title} - {activeStepConfig.subtitle}</span>
                <span className="text-slate-600">© MandiSense AI Evaluator Simulation Framework</span>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
