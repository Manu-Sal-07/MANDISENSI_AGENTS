import { Card, CardContent } from "@/components/ui/card";
import { XCircle } from "lucide-react";

export function FailureCard() {
  return (
    <Card className="bg-card border-amber-500/30 shadow-sm shadow-amber-500/5">
      <CardContent className="p-4 flex flex-col space-y-3">
        <div className="flex items-center gap-2 text-amber-500">
          <XCircle className="w-4 h-4" />
          <span className="text-sm font-bold uppercase tracking-wide">Last Incorrect Prediction</span>
        </div>
        <div className="bg-background border border-border rounded-md p-3 space-y-2 text-sm">
          <p className="text-muted-foreground"><span className="text-foreground font-semibold">When:</span> 2 weeks ago (Potato)</p>
          <p className="text-muted-foreground"><span className="text-foreground font-semibold">Why we missed it:</span> Sudden unseasonal rain caused an unexpected supply disruption that our models didn't account for.</p>
        </div>
      </CardContent>
    </Card>
  );
}
