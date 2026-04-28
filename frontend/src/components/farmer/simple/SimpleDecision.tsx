"use client";

import { UI_TEXT } from "./content";
import { CheckCircle2, Clock } from "lucide-react";

interface SimpleDecisionProps {
  decision: "SELL" | "WAIT";
  priceMin: number;
  priceMax: number;
  confidence: "High" | "Medium" | "Low";
  risk: "High" | "Medium" | "Low";
}

export function SimpleDecision({ decision, priceMin, priceMax, confidence, risk }: SimpleDecisionProps) {
  const isSell = decision === "SELL";
  
  // Decide base colors
  const primaryColor = isSell ? "text-emerald-500" : "text-amber-500";
  const bgSoft = isSell ? "bg-emerald-500/10" : "bg-amber-500/10";
  const borderColor = isSell ? "border-emerald-500/50" : "border-amber-500/50";
  
  return (
    <div className={`flex flex-col items-center justify-center p-8 rounded-2xl border-4 ${borderColor} ${bgSoft} text-center space-y-6 shadow-lg shadow-black/5`}>
      
      {/* Primary Decision */}
      <div className="flex flex-col items-center space-y-2">
        {isSell ? <CheckCircle2 className={`w-16 h-16 ${primaryColor}`} /> : <Clock className={`w-16 h-16 ${primaryColor}`} />}
        <h1 className={`text-6xl font-black tracking-tight ${primaryColor}`}>
          {UI_TEXT.decision[decision]}
        </h1>
        <p className="text-2xl font-bold text-foreground opacity-90 mt-2">
          {decision === "SELL" ? "Today" : UI_TEXT.timeWindow}
        </p>
      </div>

      <div className="w-full border-t-2 border-border/50"></div>

      {/* Price Target */}
      <div className="flex flex-col items-center">
        <span className="text-4xl font-black text-foreground">
          ₹{priceMin} – ₹{priceMax}
        </span>
      </div>

      {/* Context Tags */}
      <div className="flex gap-4 w-full justify-center pt-2">
        <div className="flex flex-col items-center">
          <span className="text-sm font-semibold text-muted-foreground uppercase">{UI_TEXT.confidenceLabel}</span>
          <span className={`text-lg font-bold ${confidence === "High" ? "text-emerald-500" : confidence === "Medium" ? "text-amber-500" : "text-rose-500"}`}>
            {confidence}
          </span>
        </div>
        <div className="flex flex-col items-center">
          <span className="text-sm font-semibold text-muted-foreground uppercase">{UI_TEXT.riskLabel}</span>
          <span className={`text-lg font-bold ${risk === "Low" ? "text-emerald-500" : risk === "Medium" ? "text-amber-500" : "text-rose-500"}`}>
            {risk}
          </span>
        </div>
      </div>
      
    </div>
  );
}
