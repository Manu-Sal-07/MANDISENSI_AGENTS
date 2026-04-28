import { Card, CardContent } from "@/components/ui/card";
import { Check, AlertTriangle } from "lucide-react";

interface DecisionComparisonCardProps {
  sell: {
    min: number;
    max: number;
    safe: boolean;
  };
  wait: {
    expected: number;
    risk_price: number;
  };
}

export function DecisionComparisonCard({ sell, wait }: DecisionComparisonCardProps) {
  return (
    <Card className="bg-card overflow-hidden">
      <div className="flex flex-col sm:flex-row divide-y sm:divide-y-0 sm:divide-x divide-border">
        
        {/* SELL NOW Column */}
        <div className="flex-1 p-4 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-foreground">SELL NOW</h3>
            {sell.safe && (
              <span className="flex items-center gap-1 text-xs font-bold text-emerald-500 bg-emerald-500/20 px-2 py-0.5 rounded-full">
                <Check className="w-3 h-3" /> Safe
              </span>
            )}
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Expected Price</p>
            <p className="text-2xl font-bold text-emerald-500">₹{sell.min} – ₹{sell.max}</p>
          </div>
        </div>

        {/* WAIT Column */}
        <div className="flex-1 p-4 bg-amber-500/5 hover:bg-amber-500/10 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-foreground">WAIT</h3>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">Expected Price</p>
              <p className="text-2xl font-bold text-amber-500">₹{wait.expected}</p>
            </div>
            <div className="flex items-start gap-2 text-rose-500 bg-rose-500/10 p-2 rounded-md">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <p className="text-xs font-medium">Risk: may drop to ₹{wait.risk_price}</p>
            </div>
          </div>
        </div>

      </div>
    </Card>
  );
}
