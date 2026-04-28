import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle } from "lucide-react";

interface ProbabilityCardProps {
  sell_prob: number;
  wait_prob: number;
}

export function ProbabilityCard({ sell_prob, wait_prob }: ProbabilityCardProps) {
  const sellRisk = 100 - sell_prob;
  const waitRisk = 100 - wait_prob;

  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <HelpCircle className="w-5 h-5 text-primary" />
          What are the chances?
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 mt-2">
        
        {/* Sell Now Probabilities */}
        <div className="space-y-2">
          <div className="flex justify-between items-end">
            <span className="font-bold text-sm text-foreground">SELL NOW</span>
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-emerald-500 font-medium">Good Price ({sell_prob}%)</span>
              <span className="text-rose-500 font-medium">Slight Drop ({sellRisk}%)</span>
            </div>
            {/* Progress Bar Visual */}
            <div className="h-2 w-full bg-rose-500/20 rounded-full overflow-hidden flex">
              <div 
                className="h-full bg-emerald-500 rounded-l-full" 
                style={{ width: `${sell_prob}%` }}
              />
              <div 
                className="h-full bg-rose-500 rounded-r-full" 
                style={{ width: `${sellRisk}%` }}
              />
            </div>
          </div>
        </div>

        {/* Wait Probabilities */}
        <div className="space-y-2">
          <div className="flex justify-between items-end">
            <span className="font-bold text-sm text-foreground">WAIT</span>
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-emerald-500 font-medium">Higher Price ({wait_prob}%)</span>
              <span className="text-rose-500 font-medium">Price Drop ({waitRisk}%)</span>
            </div>
            {/* Progress Bar Visual */}
            <div className="h-2 w-full bg-rose-500/20 rounded-full overflow-hidden flex">
              <div 
                className="h-full bg-emerald-500 rounded-l-full" 
                style={{ width: `${wait_prob}%` }}
              />
              <div 
                className="h-full bg-rose-500 rounded-r-full" 
                style={{ width: `${waitRisk}%` }}
              />
            </div>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}
