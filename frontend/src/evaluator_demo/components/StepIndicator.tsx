import React from 'react';
import { Check, Play, Circle, Loader2 } from 'lucide-react';
import { WorkflowStepConfig, WorkflowStepId } from '../workflowConfig';

interface StepIndicatorProps {
  steps: WorkflowStepConfig[];
  currentStepId: WorkflowStepId | null;
  currentProgress: number; // 0 to 100
  isSimulating: boolean;
}

export default function StepIndicator({
  steps,
  currentStepId,
  currentProgress,
  isSimulating,
}: StepIndicatorProps) {
  return (
    <div className="flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Workflow Progress
        </span>
        {isSimulating && currentStepId && (
          <span className="flex items-center gap-1.5 text-[10px] font-bold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded-full border border-sky-500/20 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" />
            STEP {currentStepId}/8
          </span>
        )}
      </div>

      <div className="relative pl-4">
        {/* Timeline connector track */}
        <div className="absolute left-[31px] top-6 bottom-6 w-[2px] bg-slate-800" />
        
        {/* Active connector track highlight */}
        {currentStepId && (
          <div 
            className="absolute left-[31px] top-6 w-[2px] bg-gradient-to-b from-emerald-500 to-sky-500 transition-all duration-300"
            style={{
              height: `calc(${((currentStepId - 1) / (steps.length - 1)) * 100}% - 12px)`
            }}
          />
        )}

        <div className="space-y-6">
          {steps.map((step) => {
            const isCompleted = currentStepId ? step.id < currentStepId : false;
            const isActive = currentStepId === step.id;
            const isPending = currentStepId ? step.id > currentStepId : true;

            return (
              <div 
                key={step.id} 
                className={`relative flex items-start gap-4 transition-all duration-300 ${
                  isActive ? 'opacity-100' : isCompleted ? 'opacity-85' : 'opacity-40'
                }`}
              >
                {/* Step Index Node */}
                <div className="relative z-10 flex items-center justify-center">
                  {isCompleted ? (
                    <div className="w-8 h-8 rounded-full bg-emerald-950 border border-emerald-500 flex items-center justify-center shadow-[0_0_12px_rgba(52,211,153,0.3)]">
                      <Check className="w-4 h-4 text-emerald-400" />
                    </div>
                  ) : isActive ? (
                    <div className="relative w-8 h-8 rounded-full bg-slate-900 border-2 border-sky-400 flex items-center justify-center shadow-[0_0_15px_rgba(56,189,248,0.4)]">
                      <span className="text-xs font-bold text-sky-400">{step.id}</span>
                      <div className="absolute inset-0 rounded-full border border-sky-400 animate-ping opacity-35" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-slate-950 border border-slate-700 flex items-center justify-center">
                      <span className="text-xs font-bold text-slate-500">{step.id}</span>
                    </div>
                  )}
                </div>

                {/* Step Info Content */}
                <div className="flex-1 min-w-0 pt-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className={`text-sm font-semibold tracking-wide truncate ${
                      isActive ? 'text-sky-300' : isCompleted ? 'text-emerald-400' : 'text-slate-400'
                    }`}>
                      {step.title}
                    </h4>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {(step.duration / 1000).toFixed(1)}s
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5 truncate">{step.subtitle}</p>

                  {/* Active Step Progress Indicator */}
                  {isActive && (
                    <div className="mt-2 w-full bg-slate-900 rounded-full h-1 overflow-hidden border border-slate-800">
                      <div 
                        className="bg-gradient-to-r from-sky-500 to-emerald-500 h-full transition-all duration-100 ease-linear"
                        style={{ width: `${currentProgress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
