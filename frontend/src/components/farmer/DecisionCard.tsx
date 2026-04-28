import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, Clock } from "lucide-react";

interface DecisionCardProps {
  decision: "SELL" | "WAIT";
  days: string;
}

export function DecisionCard({ decision, days }: DecisionCardProps) {
  const isSell = decision === "SELL";
  
  return (
    <Card className={`border-2 ${isSell ? 'border-emerald-500/50 bg-emerald-500/10' : 'border-amber-500/50 bg-amber-500/10'}`}>
      <CardContent className="pt-6 flex flex-col items-center text-center space-y-4">
        <div className="flex items-center justify-center space-x-2">
          {isSell ? <CheckCircle2 className="w-8 h-8 text-emerald-500" /> : <Clock className="w-8 h-8 text-amber-500" />}
          <h1 className={`text-5xl font-black tracking-tight ${isSell ? 'text-emerald-500' : 'text-amber-500'}`}>
            {decision}
          </h1>
        </div>
        <p className="text-xl font-medium text-foreground">
          in the next <span className="font-bold">{days} days</span>
        </p>
      </CardContent>
    </Card>
  );
}
