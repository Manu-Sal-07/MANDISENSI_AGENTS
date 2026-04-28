import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sunrise, CheckCircle2, AlertTriangle, TrendingUp } from "lucide-react";

export function DailyAdviceCard() {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <Sunrise className="w-5 h-5 text-amber-500" />
          Today's Quick Guide
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 mt-2">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
          <span className="text-foreground font-medium">Good time to sell tomatoes</span>
        </div>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <span className="text-foreground font-medium">Avoid onions today</span>
        </div>
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
          <span className="text-foreground font-medium">Demand rising</span>
        </div>
      </CardContent>
    </Card>
  );
}
