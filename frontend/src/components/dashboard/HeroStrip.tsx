"use client";

import { CheckCircle2, Clock } from "lucide-react";
import { motion } from "framer-motion";

interface HeroStripProps {
  decision: "SELL" | "WAIT";
  priceMin: number;
  priceMax: number;
  confidence: "High" | "Medium" | "Low";
  risk: "High" | "Medium" | "Low";
}

export function HeroStrip({ decision, priceMin, priceMax, confidence, risk }: HeroStripProps) {
  const isSell = decision === "SELL";
  const glow = isSell ? "shadow-[0_0_40px_rgba(34,197,94,0.25)] border-emerald-500/30" : "shadow-[0_0_40px_rgba(245,158,11,0.25)] border-amber-500/30";
  const bgGrad = isSell ? "from-emerald-950/40 via-slate-900 to-slate-950" : "from-amber-950/40 via-slate-900 to-slate-950";
  const primaryColor = isSell ? "text-emerald-500" : "text-amber-500";

  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`mx-4 mt-2 p-5 rounded-2xl border bg-gradient-to-br ${bgGrad} ${glow} backdrop-blur-2xl z-20 sticky top-[72px]`}
    >
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
        {/* Icon & Decision */}
        <div className="flex items-center gap-4">
        <div className={`p-3 rounded-full bg-background/50 border border-border/50 shadow-inner`}>
          {isSell ? <CheckCircle2 className={`w-8 h-8 ${primaryColor}`} /> : <Clock className={`w-8 h-8 ${primaryColor}`} />}
        </div>
        <div className="flex flex-col">
          <span className={`text-4xl font-black tracking-tighter ${primaryColor}`}>{decision}</span>
          <span className="text-sm font-bold text-muted-foreground uppercase tracking-widest">{isSell ? "Action Now" : "Hold Position"}</span>
        </div>
      </div>

      {/* Circular Indicators (Simulated with rich UI) */}
      <div className="flex gap-4">
        <div className="flex flex-col items-center">
          <div className="relative w-12 h-12 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="4" fill="none" className="text-slate-800" />
              <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="4" fill="none" 
                strokeDasharray="125" strokeDashoffset={confidence === "High" ? "25" : confidence === "Medium" ? "60" : "90"} 
                className={confidence === "High" ? "text-emerald-500" : "text-amber-500"} 
                strokeLinecap="round" />
            </svg>
            <span className="absolute text-[10px] font-bold text-foreground">CONF</span>
          </div>
        </div>

        <div className="flex flex-col items-center">
          <div className="relative w-12 h-12 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="4" fill="none" className="text-slate-800" />
              <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="4" fill="none" 
                strokeDasharray="125" strokeDashoffset={risk === "High" ? "25" : risk === "Medium" ? "60" : "100"} 
                className={risk === "High" ? "text-rose-500" : risk === "Medium" ? "text-amber-500" : "text-emerald-500"} 
                strokeLinecap="round" />
            </svg>
            <span className="absolute text-[10px] font-bold text-foreground">RISK</span>
          </div>
        </div>
      </div>
      </div>
    </motion.div>
  );
}
