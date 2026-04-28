import { CheckCircle2, Clock, AlertTriangle, ShieldCheck } from "lucide-react";

interface DecisionStripProps {
  decision: "SELL" | "WAIT";
  priceMin: number;
  priceMax: number;
  confidence: "High" | "Medium" | "Low";
  risk: "High" | "Medium" | "Low";
}

export function DecisionStrip({ decision, priceMin, priceMax, confidence, risk }: DecisionStripProps) {
  const isSell = decision === "SELL";
  const primaryColor = isSell ? "text-emerald-500" : "text-amber-500";
  const bgSoft = isSell ? "bg-emerald-500/10" : "bg-amber-500/10";
  const borderCol = isSell ? "border-emerald-500/30" : "border-amber-500/30";

  return (
    <div className={`flex-none flex items-center justify-between p-4 ${bgSoft} border-b ${borderCol} shadow-sm z-10`}>
      {/* Left side: Decision & Price */}
      <div className="flex items-center gap-4">
        <div className={`flex items-center justify-center w-12 h-12 rounded-full ${isSell ? 'bg-emerald-500/20' : 'bg-amber-500/20'}`}>
          {isSell ? <CheckCircle2 className={`w-6 h-6 ${primaryColor}`} /> : <Clock className={`w-6 h-6 ${primaryColor}`} />}
        </div>
        <div className="flex flex-col">
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-black tracking-tight ${primaryColor}`}>{decision}</span>
            <span className="text-xs font-bold text-muted-foreground uppercase">{isSell ? "Today" : "Wait 2-4 days"}</span>
          </div>
          <span className="text-lg font-bold text-foreground">₹{priceMin} – ₹{priceMax}</span>
        </div>
      </div>

      {/* Right side: Conf & Risk */}
      <div className="flex flex-col items-end gap-1">
        <div className="flex items-center gap-1.5 text-xs font-bold">
          <ShieldCheck className={`w-3.5 h-3.5 ${confidence === 'High' ? 'text-emerald-500' : 'text-amber-500'}`} />
          <span className="text-muted-foreground uppercase">Conf:</span>
          <span className="text-foreground">{confidence}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-bold">
          <AlertTriangle className={`w-3.5 h-3.5 ${risk === 'High' ? 'text-rose-500' : risk === 'Medium' ? 'text-amber-500' : 'text-emerald-500'}`} />
          <span className="text-muted-foreground uppercase">Risk:</span>
          <span className="text-foreground">{risk}</span>
        </div>
      </div>
    </div>
  );
}
