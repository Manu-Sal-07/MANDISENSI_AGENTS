import { Card, CardContent } from "@/components/ui/card";
import { Activity, ArrowDownRight } from "lucide-react";

interface ConfidenceChangeCardProps {
  oldConf: number;
  newConf: number;
}

export function ConfidenceChangeCard({ oldConf, newConf }: ConfidenceChangeCardProps) {
  return (
    <Card className="bg-card">
      <CardContent className="p-4 flex flex-col items-center text-center space-y-3">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Activity className="w-4 h-4" />
          <span className="text-sm font-medium uppercase tracking-widest">Confidence Dropped</span>
        </div>
        
        <div className="flex items-center gap-3 text-2xl font-bold">
          <span className="text-emerald-500">{oldConf}%</span>
          <ArrowDownRight className="w-5 h-5 text-rose-500" />
          <span className="text-rose-500">{newConf}%</span>
        </div>

        <div className="text-xs text-muted-foreground bg-muted p-2 rounded-md w-full">
          <span className="font-semibold text-foreground">Reason:</span> Conflicting signals
        </div>
      </CardContent>
    </Card>
  );
}
