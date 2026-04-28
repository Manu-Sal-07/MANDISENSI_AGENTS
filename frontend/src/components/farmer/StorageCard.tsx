import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Warehouse, CheckCircle2, AlertTriangle } from "lucide-react";

export function StorageCard() {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <Warehouse className="w-5 h-5 text-primary" />
          Storage Trade-off
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 mt-2">
        
        <div className="space-y-2 p-3 bg-amber-500/5 rounded-lg border border-amber-500/20">
          <p className="font-bold text-amber-500">If you STORE:</p>
          <div className="flex items-start gap-2 text-sm text-foreground">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <span>Possible higher price next week</span>
          </div>
          <div className="flex items-start gap-2 text-sm text-foreground">
            <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <span>Spoilage risk reduces total quantity</span>
          </div>
        </div>

        <div className="space-y-2 p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/20">
          <p className="font-bold text-emerald-500">If you SELL NOW:</p>
          <div className="flex items-start gap-2 text-sm text-foreground">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <span>100% safe, no spoilage risk</span>
          </div>
        </div>

      </CardContent>
    </Card>
  );
}
