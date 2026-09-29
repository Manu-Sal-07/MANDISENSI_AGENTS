import React, { useState, useEffect } from 'react';
import { Compass, BookOpen, ToggleLeft, ToggleRight, HelpCircle } from 'lucide-react';
import WhyItMattersCard from './WhyItMattersCard';
import TechnicalInsightsPanel from './TechnicalInsightsPanel';

interface NarrationPanelProps {
  stepId: number;
  progress: number;
  onOpenQuestions: () => void;
}

export default function NarrationPanel({ stepId, progress, onOpenQuestions }: NarrationPanelProps) {
  const [learnMoreExpanded, setLearnMoreExpanded] = useState(false);
  const [technicalView, setTechnicalView] = useState(false);

  // Auto-collapse Learn More on step change so the next step description is clean
  useEffect(() => {
    setLearnMoreExpanded(false);
  }, [stepId]);

  // Determine current narration data based on stepId and progress
  const getNarrationData = () => {
    switch (stepId) {
      case 1:
      case 2:
        return {
          title: "Step 1: Understanding the Query",
          text: "The system extracts the commodity, market, quantity, intent, and time horizon from the user's request.",
          learnMore: "NLP processing separates domain descriptors (like Kolar market, tomato commodity) from transaction verbs (sell, buy). This constructs the target forecast coordinates."
        };
      case 3:
        return {
          title: "Step 2: Seasonality Agent",
          text: "This agent studies historical price cycles, recurring demand patterns, and festival-driven behavior to estimate future movement.",
          learnMore: "Cyclical patterns repeat due to crop harvest periods. MandiSense isolates recurring fluctuations from transient shocks using periodograms."
        };
      case 4:
        return {
          title: "Step 3: Arrival Volume Agent",
          text: "This agent evaluates supply conditions, market arrivals, elasticity, and supply shocks.",
          learnMore: "Supply stress measures how current arrivals differ from expected arrivals. Higher stress indicates tighter supply and stronger upward pressure on prices."
        };
      case 5:
        return {
          title: "Step 4: External Factors Agent",
          text: "This agent monitors weather conditions, policy events, and market news that may influence prices.",
          learnMore: "Exogenous signals like minimum support prices (MSP) or weather hazards like sudden rainfall affect short-term trading patterns."
        };
      case 6:
        if (progress < 75) {
          return {
            title: "Step 5: Meta Ensemble",
            text: "Independent agent outputs are combined using confidence-aware weighting to create a balanced prediction.",
            learnMore: "Different agents excel in different market states. The ensemble assigns weight dynamically so that high-confidence outputs dominate."
          };
        } else {
          return {
            title: "Step 6: Attribution Analysis",
            text: "The system reveals which intelligence sources contributed most to the final recommendation.",
            learnMore: "Attribution analysis exposes the inner reasoning of the fusion core, breaking down contributions into distinct percentage channels."
          };
        }
      case 7:
      case 8:
        return {
          title: "Step 7: Final Recommendation",
          text: "The final recommendation is generated after combining all available evidence and confidence signals.",
          learnMore: "The recommendation triggers a strong Buy/Sell signal only when expected return values exceed local trading risk tolerances."
        };
      default:
        return {
          title: "Awaiting Simulation Launch",
          text: "Click 'Run System' on the left to start the self-guided forecasting narration.",
          learnMore: "No active execution stack detected."
        };
    }
  };

  const narration = getNarrationData();

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-2xl backdrop-blur-xl space-y-4 flex flex-col justify-between">
      
      {/* Title bar */}
      <div className="flex items-center gap-2 border-b border-slate-900 pb-3">
        <div className="w-6 h-6 rounded bg-sky-950 border border-sky-500/20 flex items-center justify-center">
          <Compass className="w-3.5 h-3.5 text-sky-400" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono">What MandiSense Is Doing</h4>
          <p className="text-[9px] text-slate-500 font-mono">STEP_OBSERVABILITY_PANEL</p>
        </div>
      </div>

      {/* Narration content */}
      <div className="space-y-3 font-mono text-[10px] text-slate-350 min-h-[85px] leading-relaxed">
        <span className="text-[9px] text-sky-400 font-bold block uppercase">{narration.title}</span>
        <p className="text-slate-300">{narration.text}</p>
      </div>

      {/* Learn More Toggle */}
      <div className="border-t border-slate-900/60 pt-3">
        <button
          onClick={() => setLearnMoreExpanded(!learnMoreExpanded)}
          className="flex items-center gap-1.5 text-sky-400 hover:text-sky-300 font-bold text-[9px] font-mono uppercase tracking-wider transition-colors"
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>{learnMoreExpanded ? 'Collapse Details' : 'Learn More'}</span>
        </button>

        {learnMoreExpanded && (
          <div className="mt-2.5 p-3 rounded-lg border border-slate-905 bg-slate-900/40 text-slate-400 font-mono text-[9px] leading-relaxed animate-[fadeIn_0.25s_ease-out]">
            {narration.learnMore}
          </div>
        )}
      </div>

      {/* Why It Matters */}
      <WhyItMattersCard stepId={stepId} />

      {/* Technical Toggle */}
      <div className="flex items-center justify-between border-t border-slate-900/60 pt-3 font-mono text-[9px]">
        <span className="text-slate-500 uppercase font-bold">Technical View:</span>
        <button 
          onClick={() => setTechnicalView(!technicalView)}
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          {technicalView ? (
            <ToggleRight className="w-7 h-7 text-sky-400" />
          ) : (
            <ToggleLeft className="w-7 h-7 text-slate-600" />
          )}
        </button>
      </div>

      {technicalView && (
        <TechnicalInsightsPanel stepId={stepId} />
      )}

      {/* Viva Questions button */}
      <button
        onClick={onOpenQuestions}
        className="w-full py-2 px-3 border border-sky-500/20 hover:border-sky-500/40 bg-sky-950/10 hover:bg-sky-950/20 rounded-lg text-sky-400 hover:text-sky-300 font-bold text-[10px] tracking-wider font-mono uppercase transition-all shadow-[0_0_12px_rgba(56,189,248,0.05)] flex items-center justify-center gap-1.5 active:scale-[0.98]"
      >
        <HelpCircle className="w-3.5 h-3.5" />
        Ask About This Step
      </button>

    </div>
  );
}
