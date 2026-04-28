"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Clock, ShieldCheck, AlertTriangle } from "lucide-react";

interface HeroPanelProps {
  decision: "SELL" | "WAIT";
  priceMin: number;
  priceMax: number;
  confidence: "High" | "Medium" | "Low";
  risk: "High" | "Medium" | "Low";
}

export function HeroPanel({ decision, priceMin, priceMax, confidence, risk }: HeroPanelProps) {
  const isSell = decision === "SELL";
  const primaryColor = isSell ? "text-emerald-500" : "text-amber-500";
  const glowShadow = isSell 
    ? "shadow-[0_0_50px_rgba(16,185,129,0.2)]" 
    : "shadow-[0_0_50px_rgba(245,158,11,0.2)]";

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full p-8 rounded-3xl bg-slate-900/40 border border-white/10 backdrop-blur-xl ${glowShadow} relative overflow-hidden mb-6`}
    >
      {/* Decorative Gradient Background */}
      <div className={`absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l ${isSell ? 'from-emerald-500/10' : 'from-amber-500/10'} to-transparent`} />

      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="flex items-center gap-6">
          <div className={`p-5 rounded-2xl bg-slate-950/60 border border-white/5 shadow-inner`}>
            {isSell ? <CheckCircle2 className="w-12 h-12 text-emerald-500" /> : <Clock className="w-12 h-12 text-amber-500" />}
          </div>
          <div className="flex flex-col">
            <h1 className={`text-6xl font-black tracking-tighter ${primaryColor}`}>
              {decision}
            </h1>
            <p className="text-xl font-bold text-slate-400 mt-1 uppercase tracking-widest">
              Market Advice
            </p>
          </div>
        </div>

        <div className="flex flex-col items-center md:items-end text-center md:text-right">
          <span className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-1">Target Range</span>
          <span className="text-5xl font-black text-white tracking-tight">
            ₹{priceMin} – ₹{priceMax}
          </span>
        </div>

        <div className="flex items-center gap-8 bg-slate-950/40 p-6 rounded-2xl border border-white/5">
          <div className="flex flex-col items-center">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="none" className="text-slate-800" />
                <circle 
                  cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="none" 
                  strokeDasharray="176" 
                  strokeDashoffset={confidence === "High" ? "35" : confidence === "Medium" ? "88" : "130"} 
                  className={isSell ? "text-emerald-500" : "text-amber-500"} 
                  strokeLinecap="round" 
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <ShieldCheck className="w-4 h-4 text-slate-400" />
              </div>
            </div>
            <span className="text-[10px] font-bold text-slate-500 mt-2">CONFIDENCE</span>
          </div>

          <div className="flex flex-col items-center">
             <div className={`w-14 h-14 rounded-full flex items-center justify-center bg-slate-900 border ${risk === 'High' ? 'border-rose-500/50 text-rose-500' : 'border-emerald-500/50 text-emerald-500'}`}>
                <AlertTriangle className="w-7 h-7" />
             </div>
             <span className="text-[10px] font-bold text-slate-500 mt-2">RISK: {risk.toUpperCase()}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
