'use client';

import React from 'react';
import { X, Database, Layers, Network, Brain } from 'lucide-react';
import { AgentId } from './hooks/useDecisionJourney';

interface AgentReasoningModalProps {
  agentId: AgentId;
  onClose: () => void;
}

interface ModelItem {
  name: string;
  desc: string;
}

interface AgentDetail {
  title: string;
  description: string;
  inputs: string[];
  models: ModelItem[];
  prediction: string;
  confidence: string;
  trainedModels: string;
  accentColor: string;
}

export default function AgentReasoningModal({ agentId, onClose }: AgentReasoningModalProps) {
  if (!agentId) return null;

  // Modal data registry typed explicitly
  const agentDetails: Record<'seasonality' | 'arrival' | 'external' | 'ensemble', AgentDetail> = {
    seasonality: {
      title: 'Seasonality Agent Diagnostics',
      description: 'Analyzes long-term cyclical patterns and seasonal deviations.',
      inputs: [
        'Historical Mandi Prices (5-year price indices)',
        'Seasonal Crop Cycles (Kharif/Rabi harvest timings)',
        'Festival Demand Spikes (Spike indices for Diwali, Eid, Pongal)',
        'Short-term trend momentum indicators',
      ],
      models: [
        { name: 'STL Decomposition', desc: 'Time-series seasonal baseline' },
        { name: 'Ridge Regression', desc: 'Regularized trend-cycle estimator' },
        { name: 'Lasso Regression', desc: 'Sparsity-inducing feature selector' },
        { name: 'Random Forest Regressor', desc: 'Non-linear cycle decision boundaries' },
        { name: 'XGBoost Regressor', desc: 'Gradient boosted residuals model' },
        { name: 'LightGBM Regressor', desc: 'Fast leaf-wise trend learner' },
        { name: 'SARIMA Forecast', desc: 'Seasonal autoregressive seasonal predictor' },
        { name: 'Simple Moving Average', desc: 'Baseline smoothing model' },
        { name: 'Multi-lag Autoregressive', desc: 'Autoregressive lags (1, 7, 14, 30 days)' },
      ],
      prediction: '+4.2% Price Shift',
      confidence: '92%',
      trainedModels: '9 Models Trained',
      accentColor: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]',
    },
    arrival: {
      title: 'Arrival Agent Diagnostics',
      description: 'Estimates supply stress by evaluating mandi arrival volumes.',
      inputs: [
        'Mandi Inflow Volumes (Kolar, Bangalore, Chintamani registries)',
        'Crop Supply Stress indexes (Regional crop acreage)',
        'Mandi Arrival Trends (Year-over-year volume comparison)',
        'In-transit Market flow volume estimates',
      ],
      models: [
        { name: 'Regression Inflow Forecaster', desc: 'Regression-based sequence volume estimator' },
        { name: 'Prophet Arrival Model', desc: 'Additive trend + holiday components' },
        { name: 'Random Forest Regressor', desc: 'Arrival volume estimator' },
        { name: 'XGBoost Regressor', desc: 'Arrival volatility estimator' },
        { name: 'ElasticNet Regressor', desc: 'Short-term arrival linear regularizer' },
        { name: 'ARIMA Inflow Model', desc: 'Autoregressive volume baseline' },
        { name: 'AutoARIMA Volume Model', desc: 'Optimized parameter selector' },
        { name: 'Double Exponential Smoothing', desc: 'Holt-Winters volume smoother' },
      ],
      prediction: '+5.1% Supply Deficit',
      confidence: '89%',
      trainedModels: '8 Models Trained',
      accentColor: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5 shadow-[0_0_15px_rgba(6,182,212,0.15)]',
    },
    external: {
      title: 'External Factors Agent Diagnostics',
      description: 'Assesses macroeconomic and climate signals.',
      inputs: [
        'Local & Regional Weather Forecasts (IMD precipitation gauges)',
        'Agricultural Market News (Agri-sector sentiment classification)',
        'Govt Policy shifts & MSP (Minimum Support Price updates)',
        'Logistics & Fuel prices (Diesel freight surcharge indexes)',
      ],
      models: [
        { name: 'Policy Sentiment Classifier', desc: 'Lexicon-based policy document classifier' },
        { name: 'IMD Weather Impact Regressor', desc: 'Rainfall correlation coefficient' },
        { name: 'Diesel Cost Indexer', desc: 'Logistics surcharge impact estimator' },
        { name: 'MSP Corridor Filter', desc: 'MSP floor boundary checker' },
        { name: 'Interstate Trade Regressor', desc: 'Cross-border supply volume model' },
        { name: 'News Sentiment Tf-Idf Classifier', desc: 'Text-frequency agribusiness sentiment classifier' },
      ],
      prediction: '-0.7% Market Stress',
      confidence: '90%',
      trainedModels: '6 Models Trained',
      accentColor: 'text-violet-400 border-violet-500/20 bg-violet-500/5 shadow-[0_0_15px_rgba(139,92,246,0.15)]',
    },
    ensemble: {
      title: 'Meta Ensemble Diagnostics',
      description: 'Fuses sub-agent outputs using dynamic confidence-weighted voting.',
      inputs: [],
      models: [],
      prediction: 'HOLD TOMATO FOR 7 DAYS',
      confidence: '84%',
      trainedModels: 'Dynamic Weights Applied',
      accentColor: 'text-indigo-400 border-indigo-500/20 bg-indigo-500/5 shadow-[0_0_15px_rgba(99,102,241,0.15)]',
    },
  };

  // Safe cast since null check was performed
  const activeKey = agentId as Exclude<AgentId, null>;
  const info = agentDetails[activeKey];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-[fadeIn_0.2s_ease-out_both]">
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes dashflow {
          to {
            stroke-dashoffset: -20;
          }
        }
      `}} />

      {/* Modal backdrop closer */}
      <div className="absolute inset-0 cursor-default" onClick={onClose} />

      {/* Modal Content container */}
      <div className="relative z-10 w-full max-w-2xl bg-[#09101d] border border-slate-800/80 rounded-[2.5rem] p-6 md:p-8 shadow-[0_30px_60px_rgba(0,0,0,0.8),_inset_0_1px_1px_rgba(255,255,255,0.03)] overflow-hidden animate-[scaleIn_0.3s_ease-out_both]">
        {/* Glow corner decoration */}
        <div className="absolute -top-20 -right-20 w-48 h-48 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-900 pb-5 mb-6">
          <div className="space-y-1">
            <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold tracking-[0.25em] text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20 uppercase w-max">
              <Brain className="w-3.5 h-3.5" />
              Agent Diagnostic Drill-Down
            </span>
            <h3 className="text-xl font-black text-slate-100 tracking-tight">
              {info.title}
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              {info.description}
            </p>
          </div>

          <button 
            onClick={onClose} 
            className="p-2.5 rounded-xl border border-slate-900 hover:bg-slate-900 text-slate-500 hover:text-slate-350 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="space-y-6">

          {/* RENDERING SPECIFIC CONTENT FOR SUB-AGENTS */}
          {agentId !== 'ensemble' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              
              {/* Inputs block (Left column) */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5 font-mono text-[9px] text-slate-550 uppercase tracking-widest">
                  <Database className="w-3.5 h-3.5" />
                  Consumed Input Signals
                </div>

                <div className="space-y-2">
                  {info.inputs.map((inp: string, i: number) => (
                    <div key={i} className="bg-slate-950/70 border border-slate-900/60 rounded-xl p-3 text-xs text-slate-300 font-bold flex items-start gap-2.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <span className="leading-snug">{inp}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Models block (Right column) */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5 font-mono text-[9px] text-slate-550 uppercase tracking-widest">
                  <Layers className="w-3.5 h-3.5" />
                  Trained Algorithm Stack
                </div>

                <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-800">
                  {info.models.map((mod: ModelItem, i: number) => (
                    <div key={i} className="bg-slate-950/70 border border-slate-900/60 rounded-xl p-3 text-xs flex justify-between items-center hover:border-slate-800 transition-colors">
                      <div>
                        <span className="text-slate-200 font-black block tracking-tight">{mod.name}</span>
                        <span className="text-[9px] text-slate-550 font-mono mt-0.5 block">{mod.desc}</span>
                      </div>
                      <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 px-2 py-0.5 rounded uppercase font-bold tracking-wider">
                        Active
                      </span>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          ) : (
            // RENDERING REASONING GRAPH FOR META ENSEMBLE
            <div className="space-y-6">
              <div className="flex items-center gap-1.5 font-mono text-[9px] text-slate-550 uppercase tracking-widest justify-center">
                <Network className="w-3.5 h-3.5" />
                Dynamic Weighting & Ensemble Fusion Schema
              </div>

              {/* SVGs Network graph */}
              <div className="w-full bg-slate-950/80 border border-slate-900/60 rounded-3xl p-6 flex flex-col items-center justify-center min-h-[260px] relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.06),transparent_70%)]" />

                {/* Graph Wrapper */}
                <div className="relative w-full max-w-lg h-44 flex items-center justify-between z-10">
                  
                  {/* Left Layer: 3 Agents */}
                  <div className="flex flex-col justify-between h-full">
                    {/* Seasonality */}
                    <div className="w-28 bg-slate-900/80 border border-slate-800 rounded-xl p-2.5 text-center shadow-md">
                      <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest leading-none mb-1">Seasonality Agent</span>
                      <span className="text-xs font-black text-slate-200">Weight: 38%</span>
                    </div>
                    {/* Arrival */}
                    <div className="w-28 bg-slate-900/80 border border-slate-800 rounded-xl p-2.5 text-center shadow-md">
                      <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest leading-none mb-1">Arrival Agent</span>
                      <span className="text-xs font-black text-slate-200">Weight: 47%</span>
                    </div>
                    {/* External */}
                    <div className="w-28 bg-slate-900/80 border border-slate-800 rounded-xl p-2.5 text-center shadow-md">
                      <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest leading-none mb-1">External Agent</span>
                      <span className="text-xs font-black text-slate-200">Weight: 15%</span>
                    </div>
                  </div>

                  {/* SVG connecting paths */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
                    {/* Seasonality (y: 20) to Ensemble (y: 88) */}
                    <path 
                      d="M 112 24 L 210 88" 
                      fill="none" 
                      stroke="#6366f1" 
                      strokeWidth="1.5" 
                      strokeDasharray="5,5"
                      className="animate-[dashflow_1.5s_infinite_linear]"
                    />
                    {/* Arrival (y: 88) to Ensemble (y: 88) */}
                    <path 
                      d="M 112 88 L 210 88" 
                      fill="none" 
                      stroke="#6366f1" 
                      strokeWidth="1.5" 
                      strokeDasharray="5,5"
                      className="animate-[dashflow_1.5s_infinite_linear]"
                    />
                    {/* External (y: 152) to Ensemble (y: 88) */}
                    <path 
                      d="M 112 152 L 210 88" 
                      fill="none" 
                      stroke="#6366f1" 
                      strokeWidth="1.5" 
                      strokeDasharray="5,5"
                      className="animate-[dashflow_1.5s_infinite_linear]"
                    />
                    {/* Ensemble (y: 88) to Final recommendation box (y: 88) */}
                    <path 
                      d="M 282 88 L 366 88" 
                      fill="none" 
                      stroke="#10b981" 
                      strokeWidth="2" 
                      strokeDasharray="5,5"
                      className="animate-[dashflow_1s_infinite_linear]"
                    />
                  </svg>

                  {/* Central Layer: Meta Ensemble */}
                  <div className="w-18 h-18 rounded-2xl bg-indigo-950/40 border-2 border-indigo-500 shadow-[0_0_20px_rgba(99,102,241,0.3)] flex items-center justify-center relative z-10 self-center">
                    <Layers className="w-8 h-8 text-indigo-400" />
                  </div>

                  {/* Right Layer: Final Decision */}
                  <div className="w-32 bg-slate-900 border-2 border-emerald-500/80 rounded-2xl p-3 shadow-[0_0_20px_rgba(16,185,129,0.25)] text-center relative z-10">
                    <span className="block text-[8px] font-mono text-emerald-400 uppercase tracking-widest leading-none mb-1 font-bold">Decision Engine</span>
                    <span className="text-[10px] font-black text-slate-100 block leading-tight">HOLD TOMATO FOR 7 DAYS</span>
                  </div>

                </div>
              </div>
            </div>
          )}

          {/* Modal Footer metrics display */}
          <div className="border-t border-slate-900 pt-5 mt-4 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4">
            
            {/* Model stats (Left) */}
            <div className="flex items-center gap-2.5">
              <span className={`text-[10px] font-mono font-bold tracking-wider px-3 py-1 rounded-full border ${info.accentColor}`}>
                {info.trainedModels}
              </span>
              <span className="text-[9px] font-mono text-slate-650">WEIGHTING_SCHEME: STATIC_REGIME</span>
            </div>

            {/* Prediction details (Right) */}
            <div className="flex gap-4">
              <div className="bg-slate-950/60 border border-slate-900 px-4 py-2 rounded-xl text-center min-w-[110px]">
                <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest">Prediction Outcome</span>
                <span className="text-xs font-black text-slate-200">{info.prediction}</span>
              </div>

              <div className="bg-slate-950/60 border border-slate-900 px-4 py-2 rounded-xl text-center min-w-[110px]">
                <span className="block text-[8px] font-mono text-slate-500 uppercase tracking-widest">Confidence Score</span>
                <span className="text-xs font-black text-emerald-400">{info.confidence}</span>
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
