import React from 'react';
import { Cpu } from 'lucide-react';

interface TechnicalInsightsPanelProps {
  stepId: number;
}

export default function TechnicalInsightsPanel({ stepId }: TechnicalInsightsPanelProps) {
  let models: string[] = [];
  let mathMethod = "";

  switch (stepId) {
    case 1:
    case 2:
      models = ["Spacy NLP Parser", "Custom Tokenizer Matrix", "Named Entity Recognition (NER)"];
      mathMethod = "TF-IDF + Cosine Vector Similarity";
      break;
    case 3:
      models = ["XGBoost", "Random Forest", "LightGBM", "SARIMA", "STL Linear"];
      mathMethod = "Fast Fourier Transform (FFT) Periodicity Detection";
      break;
    case 4:
      models = ["Random Forest Classifier", "Gradient Boosting Regressor", "Elasticity Linear Solver", "Polynomial Regression"];
      mathMethod = "Price Elasticity Coefficient calculation: E = %dQ / %dP";
      break;
    case 5:
      models = ["TextBlob Sentiment Analyzer", "NLTK Vader Sentiment Engine", "LSTM News Sequence Regressor", "Weather Gradient Classifier"];
      mathMethod = "Lexicon-based sentiment polling & spatial weather grids";
      break;
    case 6:
    case 7:
    case 8:
      models = ["Bayesian Pooling Regressor", "Confidence Weighted Fusion Node", "Dynamic Loss Weighting Optimizer"];
      mathMethod = "Meta Ensemble Softmax Fusion weighting formula";
      break;
    default:
      return null;
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 space-y-2 animate-[fadeIn_0.2s_ease-out] font-mono text-[9px]">
      <div className="flex items-center gap-1.5 text-slate-350 font-bold uppercase tracking-wider">
        <Cpu className="w-3.5 h-3.5 text-sky-400" />
        <span>Active Model Architecture</span>
      </div>
      
      <div className="space-y-1">
        <span className="text-slate-500 block uppercase">Ensemble Estimators:</span>
        <div className="flex flex-wrap gap-1">
          {models.map((mod, i) => (
            <span key={i} className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-900 text-slate-300 font-bold">
              {mod}
            </span>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-950 pt-2 space-y-0.5">
        <span className="text-slate-500 block uppercase">Mathematical Abstraction:</span>
        <span className="text-sky-300 block italic">{mathMethod}</span>
      </div>
    </div>
  );
}
