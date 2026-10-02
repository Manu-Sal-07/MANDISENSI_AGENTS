import React, { useEffect, useState } from 'react';
import { ShieldCheck, ArrowRight } from 'lucide-react';

interface DecisionBuilderProps {
  progress: number; // 0 to 100
  details?: { label: string; impact: string }[];
  confidence?: number;
}

interface Factor {
  label: string;
  impact: number;
  thresholdProgress: number;
}

export default function DecisionBuilder({ progress, details, confidence }: DecisionBuilderProps) {
  const [currentScore, setCurrentScore] = useState(0);

  const defaultDetails = [
    { label: "Supply Stress Impact", impact: "+24%" },
    { label: "Festival Demand Impact", impact: "+18%" },
    { label: "Weather Outlook Impact", impact: "+7%" },
    { label: "Trend Cycle Consensus", impact: "+35%" }
  ];

  const sourceDetails = details && details.length >= 4 ? details : defaultDetails;
  
  const factors: Factor[] = sourceDetails.map((item, idx) => ({
    label: item.label,
    impact: parseInt(item.impact.replace("+", "").replace("%", "")) || 0,
    thresholdProgress: (idx + 1) * 20
  }));

  const targetScoreVal = confidence || 84;

  // Calculate live score based on progress
  useEffect(() => {
    let targetScore = 0;
    if (progress >= 80) {
      targetScore = targetScoreVal;
    } else if (progress >= 60) {
      targetScore = Math.floor(targetScoreVal * 0.6);
    } else if (progress >= 40) {
      targetScore = Math.floor(targetScoreVal * 0.45);
    } else if (progress >= 20) {
      targetScore = Math.floor(targetScoreVal * 0.25);
    } else {
      targetScore = 0;
    }

    // Smooth count-up effect
    let start = currentScore;
    const end = targetScore;
    if (start === end) return;

    const range = end - start;
    const duration = 400; // ms
    let startTime: number | null = null;

    const animateCount = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const fraction = Math.min(elapsed / duration, 1);
      
      setCurrentScore(Math.floor(start + range * fraction));

      if (fraction < 1) {
        requestAnimationFrame(animateCount);
      }
    };

    requestAnimationFrame(animateCount);
  }, [progress]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-sky-950/50 border border-sky-400/40 flex items-center justify-center">
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">Decision Construction</h4>
            <p className="text-[9px] text-slate-500 font-mono">SYNTHESIZING_CONSENSUS_DNA</p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-[9px] font-mono text-slate-500 block uppercase">Consensus Score</span>
          <span className="text-lg font-bold font-mono text-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.2)]">
            {currentScore}/100
          </span>
        </div>
      </div>

      {/* Factors List */}
      <div className="space-y-2">
        {factors.map((fac, idx) => {
          const isVisible = progress >= fac.thresholdProgress;
          return (
            <div 
              key={idx}
              className={`
                flex items-center justify-between p-2.5 rounded-lg border transition-all duration-500 font-mono
                ${isVisible 
                  ? 'bg-slate-900/60 border-slate-800 text-slate-200 opacity-100 translate-x-0' 
                  : 'bg-transparent border-transparent text-slate-600 opacity-20 -translate-x-2'
                }
              `}
            >
              <div className="flex items-center gap-2">
                <span className={`text-[8px] px-1.5 py-0.5 rounded border font-extrabold ${
                  isVisible ? 'text-sky-400 border-sky-500/30 bg-sky-950/20' : 'text-slate-600 border-slate-800'
                }`}>
                  FACTOR_0{idx + 1}
                </span>
                <span className="text-[10px] font-semibold">{fac.label}</span>
              </div>

              <div className="flex items-center gap-1.5">
                <ArrowRight className={`w-3 h-3 ${isVisible ? 'text-sky-400' : 'text-slate-650'}`} />
                <span className={`text-[10px] font-bold ${isVisible ? 'text-emerald-400' : 'text-slate-600'}`}>
                  +{fac.impact}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live progress gauge */}
      <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-900 mt-2">
        <div 
          className="bg-gradient-to-r from-sky-400 to-emerald-400 h-full transition-all duration-300 ease-out"
          style={{ width: `${(currentScore / 100) * 100}%` }}
        />
      </div>
    </div>
  );
}
