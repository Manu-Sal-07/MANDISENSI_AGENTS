import { Card, CardContent } from "@/components/ui/card";
import { Frown, TrendingDown } from "lucide-react";

interface RegretCardProps {
  sell_loss: number;
  wait_loss: number;
}

export function RegretCard({ sell_loss, wait_loss }: RegretCardProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* If Sell Now */}
      <Card className="bg-card border-border/50">
        <CardContent className="p-4 flex flex-col items-center text-center space-y-2">
          <TrendingDown className="w-5 h-5 text-amber-500" />
          <p className="text-sm font-bold text-foreground">If SELL NOW</p>
          <p className="text-xs text-muted-foreground">Missed upside</p>
          <span className="text-lg font-bold text-amber-500">₹{sell_loss} / kg</span>
        </CardContent>
      </Card>

      {/* If Wait */}
      <Card className="bg-card border-rose-500/30 bg-rose-500/5">
        <CardContent className="p-4 flex flex-col items-center text-center space-y-2">
          <Frown className="w-5 h-5 text-rose-500" />
          <p className="text-sm font-bold text-foreground">If WAIT</p>
          <p className="text-xs text-rose-500/80">Possible loss</p>
          <span className="text-lg font-bold text-rose-500">₹{wait_loss} / kg</span>
        </CardContent>
      </Card>
    </div>
  );
}
