import React from 'react';
import { ArrowDown, CheckCircle, ShieldCheck } from 'lucide-react';

export default function EvaluationSummaryScreen() {
  const flowSteps = [
    { label: "User Query Input", desc: "'Can I sell 5 tons...?'", color: "border-sky-500/30 text-sky-400 bg-sky-950/20" },
    { label: "Tokenized Context", desc: "Product, Market, Action", color: "border-sky-500/30 text-sky-400 bg-sky-950/20" },
    { label: "Agent Cognition Grid", desc: "Seasonality, Supply, Climate", color: "border-amber-500/30 text-amber-400 bg-amber-950/20" },
    { label: "Meta Ensemble Fusion", desc: "Dynamic Softmax Weighting", color: "border-amber-500/30 text-amber-400 bg-amber-950/20" },
    { label: "Decision DNA Analysis", desc: "Attribution Score Distribution", color: "border-violet-500/30 text-violet-400 bg-violet-950/20" },
    { label: "Final Recommendation", desc: "SELL TODAY (+6.2% expected)", color: "border-rose-500/30 text-rose-400 bg-rose-950/20" }
  ];

  const strengths = [
    "Multi-Agent Reasoning",
    "Adaptive Ensemble Learning",
    "Dynamic Weighting",
    "Explainable Forecasting",
    "Interpretable Attribution",
    "Real-Time Decision Pipeline"
  ];

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-2xl backdrop-blur-xl space-y-6">
      
      {/* Title */}
      <div className="border-b border-slate-900 pb-3">
        <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-450 animate-pulse" />
          How This Decision Was Made
        </h4>
        <p className="text-[9px] text-slate-500 font-mono mt-1">DECISION_LOG_PATHWAY_SUMMARY</p>
      </div>

      {/* Decision flow chart vertical steps */}
      <div className="flex flex-col items-center space-y-1 font-mono text-[9px] max-w-sm mx-auto">
        {flowSteps.map((step, idx) => {
          const isLast = idx === flowSteps.length - 1;
          return (
            <React.Fragment key={idx}>
              <div 
                className={`
                  w-full px-3 py-2 border rounded-lg flex items-center justify-between text-center transition-all duration-300
                  ${step.color} shadow-sm
                `}
              >
                <span className="font-extrabold">{step.label}</span>
                <span className="text-slate-500 text-[8px]">{step.desc}</span>
              </div>
              {!isLast && (
                <ArrowDown className="w-3.5 h-3.5 text-slate-700 animate-pulse my-0.5" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* System Strengths */}
      <div className="border-t border-slate-900 pt-4 space-y-3">
        <h5 className="text-[10px] font-bold text-slate-450 uppercase tracking-wider font-mono">
          System Strengths
        </h5>
        
        <div className="grid grid-cols-2 gap-2.5">
          {strengths.map((str, i) => (
            <div key={i} className="flex items-center gap-1.5 font-mono text-[9px] text-slate-300 bg-slate-900/40 p-2 border border-slate-900 rounded-lg">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-450 shrink-0" />
              <span>{str}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
