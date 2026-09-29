import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface EvaluationHighlightsProps {
  stepId: number;
  progress: number;
}

export default function EvaluationHighlights({ stepId, progress }: EvaluationHighlightsProps) {
  const highlights = [
    { label: "Multi-Agent Architecture", thresholdStep: 3, thresholdProgress: 0 },
    { label: "Ensemble Forecasting", thresholdStep: 4, thresholdProgress: 0 },
    { label: "Real-Time Signal Fusion", thresholdStep: 5, thresholdProgress: 0 },
    { label: "Dynamic Weighting", thresholdStep: 6, thresholdProgress: 0 },
    { label: "Contribution Attribution", thresholdStep: 6, thresholdProgress: 75 },
    { label: "Explainable Decision Making", thresholdStep: 7, thresholdProgress: 0 }
  ];

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-lg backdrop-blur-xl">
      <h4 className="text-xs font-bold text-slate-350 uppercase tracking-widest font-mono mb-4 border-b border-slate-900 pb-2">
        Key Evaluation Highlights
      </h4>

      <div className="space-y-3 font-mono text-[10px]">
        {highlights.map((item, idx) => {
          // Check if this highlight has been illuminated
          const isIlluminated = 
            stepId > item.thresholdStep || 
            (stepId === item.thresholdStep && progress >= item.thresholdProgress);

          return (
            <div 
              key={idx}
              className={`
                flex items-center gap-2.5 transition-all duration-500
                ${isIlluminated ? 'text-slate-200 opacity-100' : 'text-slate-650 opacity-40'}
              `}
            >
              <CheckCircle2 className={`w-4 h-4 shrink-0 transition-colors duration-500 ${
                isIlluminated ? 'text-emerald-400 drop-shadow-[0_0_4px_rgba(52,211,153,0.4)] animate-pulse' : 'text-slate-800'
              }`} />
              <span className={isIlluminated ? 'font-semibold' : ''}>{item.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
