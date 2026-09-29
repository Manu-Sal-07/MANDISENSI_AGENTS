import React from 'react';
import { X, HelpCircle, AlertCircle } from 'lucide-react';

interface VivaQuestionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  stepId: number;
}

interface QuestionAnswer {
  q: string;
  a: string;
}

export default function VivaQuestionsDrawer({ isOpen, onClose, stepId }: VivaQuestionsDrawerProps) {
  if (!isOpen) return null;

  // Retrieve questions based on active step
  const getQuestions = (step: number): QuestionAnswer[] => {
    switch (step) {
      case 1:
      case 2:
        return [
          { q: "Why tokenize natural language query inputs?", a: "Standardizing raw user speech into query tokens (commodity, market, intent) ensures the correct forecasting indexes and historical caches are targeted without injection risk." },
          { q: "What happens if a token is unresolved?", a: "The system triggers fuzzy dictionary alignment. If still unresolved, it falls back to canonical regional aggregates." }
        ];
      case 3:
        return [
          { q: "Why use multiple models (XGBoost, SARIMA, STL) together?", a: "Linear statistical models (SARIMA) capture stable seasonality peaks, while tree ensemble models (XGBoost, LightGBM) capture complex, non-linear cyclical movements and shocks." },
          { q: "How is price seasonality detected?", a: "Using Fast Fourier Transform (FFT) periodicity detection across the past 3-5 years of daily mandi transaction price logs." },
          { q: "How do upcoming festivals influence forecasting?", a: "The system maps upcoming calendar events and matches their historical demand footprint to project holiday-driven consumption spikes." }
        ];
      case 4:
        return [
          { q: "What is supply stress?", a: "Supply stress measures the short-term deviation of current daily arrivals from their 30-day moving average trend. Higher stress indicates tight supplies." },
          { q: "How is elasticity calculated?", a: "Elasticity coefficient measures the supply-arrival percentage change relative to changes in price trends over corresponding historic cycles." },
          { q: "What happens during a supply shock?", a: "Arrival constraints tighten, driving up the consensus score to reflect immediate supply shortage pressure." }
        ];
      case 5:
        return [
          { q: "How are weather forecasts normalized?", a: "Precipitation and heat anomalies are categorized relative to historical averages during harvest seasons to estimate field disruption indexes." },
          { q: "Why is news sentiment categorized as external?", a: "News sentiment (e.g., logistics strikes, local export policies) represents exogenous factors not captured by historical price charts." }
        ];
      case 6:
        return [
          { q: "Why combine agent outputs using meta-weighting?", a: "Individual agents have localized strengths. Aggregating outputs with confidence weights prevents any single biased model from dominating the decision." },
          { q: "How are the meta weights determined?", a: "The system uses Bayesian Pooling and loss-minimization feedback loops to assign larger weights to agents displaying higher recent accuracy." }
        ];
      case 7:
      case 8:
        return [
          { q: "How is the 'Sell Today' threshold defined?", a: "It triggers when the meta ensemble's expected price change is positive and exceeds the average regional commission/transport overhead (typically +5%)." },
          { q: "How is the final confidence rating computed?", a: "Confidence is the weighted average of active agent confidence indexes, adjusted for high-conflict scenarios between agents." }
        ];
      default:
        return [
          { q: "Awaiting simulation progress", a: "Start the simulation to explore questions and answers relevant to the active system step." }
        ];
    }
  };

  const currentQuestions = getQuestions(stepId);

  return (
    <div className="fixed inset-0 z-50 flex justify-end pointer-events-none">
      {/* Dark overlay backdrop */}
      <div 
        className="absolute inset-0 bg-black/40 pointer-events-auto transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Drawer content body */}
      <div className="relative w-full max-w-md bg-slate-950 border-l border-slate-905 h-full pointer-events-auto flex flex-col shadow-2xl animate-[slideInRight_0.3s_ease-out]">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-900 flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-2 text-sky-400">
            <HelpCircle className="w-4 h-4" />
            <h4 className="font-mono font-bold text-xs uppercase tracking-wider">Viva Preparation Panel</h4>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Info notice */}
        <div className="m-4 p-3 bg-sky-950/20 border border-sky-400/20 rounded-lg flex gap-2.5 font-mono text-[9px] text-slate-400">
          <AlertCircle className="w-4 h-4 text-sky-400 shrink-0" />
          <p>This drawer prepares you for evaluator viva questions relating to the active pipeline step. All answers correspond to the actual MandiSense backend logic.</p>
        </div>

        {/* Questions List */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {currentQuestions.map((qa, index) => (
            <div key={index} className="border border-slate-900 bg-slate-950 rounded-xl p-4 space-y-2">
              <div className="text-[10px] font-extrabold font-mono text-sky-400">
                Q: {qa.q}
              </div>
              <div className="text-[10px] font-mono text-slate-400 leading-relaxed pl-1 border-l-2 border-slate-800">
                {qa.a}
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
