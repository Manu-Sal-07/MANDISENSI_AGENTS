'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, ShieldCheck, Server, Layers, Network } from 'lucide-react';

export default function ModelStackView() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="w-full bg-[#09101d]/90 backdrop-blur-xl border border-slate-900/80 rounded-[2rem] p-6 md:p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)] transition-all duration-300">
      
      {/* Clickable Header */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between cursor-pointer select-none group"
      >
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 text-indigo-400 group-hover:text-indigo-300 transition-colors">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="flex items-center gap-1 text-[8px] font-mono font-bold tracking-[0.2em] text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20 uppercase">
                Diagnostics Panel
              </span>
            </div>
            <h3 className="text-base font-black text-slate-100 group-hover:text-white transition-colors tracking-tight">
              Model Stack Assembly & Diagnostics
            </h3>
            <p className="text-xs text-slate-400 leading-none mt-1 font-sans">
              Click to inspect the hierarchical multi-agent ML assembly.
            </p>
          </div>
        </div>

        {/* Expand Trigger */}
        <div className="p-2 rounded-xl border border-slate-900 hover:bg-slate-900 text-slate-500 group-hover:text-slate-350 transition-all">
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>

      {/* Expandable Body */}
      {isOpen && (
        <div className="mt-6 pt-6 border-t border-slate-900/80 space-y-6 animate-[slideDown_0.3s_ease-out_both]">
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes slideDown {
              from { opacity: 0; transform: translateY(-8px); }
              to { opacity: 1; transform: translateY(0); }
            }
          `}} />

          {/* Assembly Overview explanation */}
          <div className="bg-slate-950/50 border border-slate-900 p-4.5 rounded-2xl">
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              <strong className="text-indigo-400 font-black">Multi-Layer Model Assembly:</strong> Rather than relying on a single monolithic ML model, FarmerOS employs a multi-tiered architecture. We train <strong className="text-white">23 sub-models</strong> independently across three specialized sub-agents. Their predictions are dynamically weighted at runtime by the Meta Ensemble to construct the final recommendation output.
            </p>
          </div>

          {/* 3 Agents Columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Column 1: Seasonality Agent Assembly (9 Models) */}
            <div className="bg-slate-950/80 border border-slate-900/60 rounded-2xl p-4.5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
                <span className="text-xs font-black text-slate-200">Seasonality Agent</span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 px-2 py-0.5 rounded font-bold">
                  9 MODELS
                </span>
              </div>
              <ul className="space-y-1.5 font-mono text-[10px] text-slate-400">
                <li className="flex justify-between"><span>• STL Decomposition</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Ridge Regression</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Lasso Regression</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Random Forest Reg.</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• XGBoost Regressor</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• LightGBM Regressor</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• SARIMA Forecast</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Simple Moving Avg.</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Multi-lag AR model</span><span className="text-slate-600">Active</span></li>
              </ul>
            </div>

            {/* Column 2: Arrival Agent Assembly (8 Models) */}
            <div className="bg-slate-950/80 border border-slate-900/60 rounded-2xl p-4.5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
                <span className="text-xs font-black text-slate-200">Arrival Agent</span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 px-2 py-0.5 rounded font-bold">
                  8 MODELS
                </span>
              </div>
              <ul className="space-y-1.5 font-mono text-[10px] text-slate-400">
                <li className="flex justify-between"><span>• Regression Inflow model</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Prophet Arrival model</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Random Forest Reg.</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• XGBoost Regressor</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• ElasticNet Regressor</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• ARIMA Inflow baseline</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• AutoARIMA baseline</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Holt-Winters Smoothing</span><span className="text-slate-600">Active</span></li>
              </ul>
            </div>

            {/* Column 3: External Factors Agent (6 Models) */}
            <div className="bg-slate-950/80 border border-slate-900/60 rounded-2xl p-4.5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-900 pb-2.5">
                <span className="text-xs font-black text-slate-200">External Agent</span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 border border-emerald-500/10 px-2 py-0.5 rounded font-bold">
                  6 MODELS
                </span>
              </div>
              <ul className="space-y-1.5 font-mono text-[10px] text-slate-400">
                <li className="flex justify-between"><span>• Policy Sentiment Classifier</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• IMD Weather Regressor</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Diesel Cost Indexer</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• MSP Price corridor filter</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• Interstate Trade Reg.</span><span className="text-slate-600">Active</span></li>
                <li className="flex justify-between"><span>• News Event Sentiment</span><span className="text-slate-600">Active</span></li>
              </ul>
            </div>

          </div>

          {/* Registry Diagnostics Footer */}
          <div className="border-t border-slate-900/80 pt-5 flex flex-wrap gap-4 items-center justify-between font-mono text-[10.5px]">
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-1.5 text-slate-450">
                <Network className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Ensemble Layer:</span>
                <strong className="text-emerald-400">ACTIVE [Dynamic weights regime]</strong>
              </div>
              <div className="flex items-center gap-1.5 text-slate-450">
                <Layers className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Learned Registry:</span>
                <strong className="text-emerald-400">ACTIVE [Weights synced]</strong>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400 font-bold bg-emerald-950/20 px-2.5 py-0.5 border border-emerald-500/20 rounded">
              <ShieldCheck className="w-3.5 h-3.5" />
              REGISTRY: ONLINE
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
