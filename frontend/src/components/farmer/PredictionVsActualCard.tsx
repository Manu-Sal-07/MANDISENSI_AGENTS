import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Target } from "lucide-react";

interface PredictionVsActualCardProps {
  predicted: string;
  actual: number;
}

export function PredictionVsActualCard({ predicted, actual }: PredictionVsActualCardProps) {
  return (
    <Card className="bg-card border-emerald-500/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <Target className="w-5 h-5 text-emerald-500" />
          Last Prediction Result
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 mt-2">
        <div className="flex justify-between items-center bg-background p-3 rounded-md border border-border">
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground uppercase tracking-widest">We Predicted</span>
            <span className="font-bold text-foreground">₹{predicted}</span>
          </div>
          <div className="flex flex-col text-right">
            <span className="text-xs text-muted-foreground uppercase tracking-widest">Actual Price</span>
            <span className="font-bold text-foreground">₹{actual}</span>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2 text-emerald-500 font-bold bg-emerald-500/10 p-2 rounded-md">
          <CheckCircle2 className="w-5 h-5" />
          Correct Prediction
        </div>
      </CardContent>
    </Card>
  );
}
