import React from 'react';
import { HelpCircle } from 'lucide-react';

interface WhyItMattersCardProps {
  stepId: number;
}

export default function WhyItMattersCard({ stepId }: WhyItMattersCardProps) {
  let contextText = "";

  switch (stepId) {
    case 1:
    case 2:
      contextText = "Accurately resolving user intent ensures correct model constraints and target market matching.";
      break;
    case 3:
      contextText = "Historical market cycles strongly influence agricultural pricing; detecting cycles prevents confusing noise with trend.";
      break;
    case 4:
      contextText = "Supply shortages often create immediate upward price pressure. Elasticity models measure how buyers react to shocks.";
      break;
    case 5:
      contextText = "Weather anomalies and policy changes can rapidly alter market behavior, overriding historical cycles.";
      break;
    case 6:
      contextText = "Balanced aggregation prevents single-source bias, shielding predictions from extreme outliers in any single model.";
      break;
    case 7:
      contextText = "Step-by-step scoring ensures complete transparency, giving evaluators full visibility into how confidence scores build up.";
      break;
    case 8:
      contextText = "Actionable intelligence reduces pricing risk for farmers, aggregators, and institutional traders during volatile shifts.";
      break;
    default:
      contextText = "Awaiting system activity to analyze operational significance.";
  }

  return (
    <div className="bg-sky-950/20 border border-sky-500/15 rounded-lg p-3.5 space-y-1.5 font-mono text-[10px] text-slate-300">
      <div className="flex items-center gap-1.5 text-sky-400 font-bold uppercase tracking-wider">
        <HelpCircle className="w-3.5 h-3.5" />
        <span>Why This Matters</span>
      </div>
      <p className="leading-relaxed text-slate-400">{contextText}</p>
    </div>
  );
}
