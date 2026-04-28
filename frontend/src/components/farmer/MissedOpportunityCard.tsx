import { Card, CardContent } from "@/components/ui/card";
import { Target } from "lucide-react";

export function MissedOpportunityCard() {
  return (
    <Card className="bg-card border-rose-500/20 shadow-sm shadow-rose-500/5">
      <CardContent className="p-4 flex flex-col space-y-2">
        <div className="flex items-center gap-2 text-rose-500">
          <Target className="w-4 h-4" />
          <span className="text-sm font-bold uppercase tracking-wide">Missed Opportunity</span>
        </div>
        <div className="flex flex-col gap-1 bg-rose-500/5 p-3 rounded-lg border border-rose-500/20 text-sm">
          <p className="text-muted-foreground font-medium">You missed:</p>
          <p className="text-rose-500 font-bold text-lg flex items-center justify-between">
            Tomato <span>+10% rise</span>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
