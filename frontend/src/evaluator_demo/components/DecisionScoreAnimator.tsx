import React from 'react';
import { motion } from 'framer-motion';
import { Cpu } from 'lucide-react';

interface DecisionScoreAnimatorProps {
  progress: number; // 0 to 100 (Step progress)
  confidence?: number;
}

export default function DecisionScoreAnimator({ progress, confidence }: DecisionScoreAnimatorProps) {
  // Score animation range: progress 70 to 95 of Step 6
  const startProgress = 70;
  const endProgress = 95;
  
  // Interpolated score
  const scoreRatio = Math.min(Math.max((progress - startProgress) / (endProgress - startProgress), 0), 1);
  const currentScore = Math.round(scoreRatio * (confidence || 84));

  const signals = [
    { label: "Supply Signal", count: 10, max: 10, color: "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]" },
    { label: "Seasonality", count: 8, max: 10, color: "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]" },
    { label: "External Signal", count: 3, max: 10, color: "bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.4)]" }
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs font-bold text-slate-350 uppercase tracking-widest font-mono">
        <Cpu className="w-4 h-4 text-sky-400" />
        <span>Decision Score Assembly</span>
      </div>

      <div className="space-y-3 font-mono">
        {signals.map((sig, sIdx) => {
          // Calculate how many bars are visible based on progress
          const activeBars = Math.min(
            Math.round(sig.count * scoreRatio),
            sig.count
          );

          return (
            <div key={sIdx} className="space-y-1">
              <div className="flex justify-between text-[9px] text-slate-500 font-bold uppercase">
                <span>{sig.label}</span>
                <span>{activeBars}/{sig.max}</span>
              </div>
              
              {/* Segmented LED bar */}
              <div className="flex gap-1 h-3.5 w-full bg-slate-950 p-0.5 rounded border border-slate-900">
                {Array.from({ length: sig.max }).map((_, bIdx) => {
                  const isFilled = bIdx < activeBars;
                  return (
                    <div 
                      key={bIdx}
                      className={`
                        flex-1 rounded-sm transition-all duration-300
                        ${isFilled ? sig.color : 'bg-slate-900'}
                      `}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Assembly score banner */}
      <div className="border border-sky-500/20 bg-sky-950/5 p-4 rounded-xl flex items-center justify-between shadow-[0_0_15px_rgba(56,189,248,0.05)]">
        <div className="font-mono">
          <span className="text-[10px] text-slate-500 block uppercase font-bold tracking-wider">Final Decision Score</span>
          <span className="text-[8px] text-sky-400 block mt-0.5">MATRIX_COEFFICIENT_SUM</span>
        </div>
        <div className="flex items-baseline gap-1 font-mono">
          <span className="text-2xl font-extrabold text-sky-400 tabular-nums">
            {currentScore}
          </span>
          <span className="text-xs text-slate-600 font-bold">/100</span>
        </div>
      </div>
    </div>
  );
}
