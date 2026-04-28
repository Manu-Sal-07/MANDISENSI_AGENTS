import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Layers } from "lucide-react";

export function TransparencyCard() {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <Layers className="w-5 h-5 text-primary" />
          How we made this decision
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 mt-2">
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-foreground">Arrival Volume</span>
            <span className="text-amber-500 font-bold">Medium impact</span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-amber-500 w-[50%]" />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-foreground">Market Demand</span>
            <span className="text-emerald-500 font-bold">High impact</span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 w-[80%]" />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-foreground">External Factors</span>
            <span className="text-rose-500 font-bold">Low impact</span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-rose-500 w-[20%]" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
