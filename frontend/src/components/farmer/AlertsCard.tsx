import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BellRing, AlertCircle, Zap } from "lucide-react";

interface AlertsCardProps {
  alerts: string[];
}

export function AlertsCard({ alerts }: AlertsCardProps) {
  if (!alerts || alerts.length === 0) return null;

  return (
    <Card className="bg-card border-rose-500/20 shadow-sm shadow-rose-500/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <BellRing className="w-5 h-5 text-rose-500" />
          Proactive Alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 mt-2">
        {alerts.map((alert, index) => {
          // simple heuristic to pick icon
          const isWarning = alert.toLowerCase().includes("drop");
          return (
            <div key={index} className={`flex items-start gap-3 p-3 rounded-lg border ${isWarning ? 'bg-rose-500/10 border-rose-500/20 text-rose-500' : 'bg-orange-500/10 border-orange-500/20 text-orange-500'}`}>
              {isWarning ? <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" /> : <Zap className="w-5 h-5 shrink-0 mt-0.5" />}
              <span className="font-semibold text-sm">{alert}</span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
