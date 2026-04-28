import { Card, CardContent } from "@/components/ui/card";
import { Activity, ShieldAlert } from "lucide-react";

interface ConfidenceCardProps {
  confidence: "High" | "Medium" | "Low";
  risk: "High" | "Medium" | "Low";
}

export function ConfidenceCard({ confidence, risk }: ConfidenceCardProps) {
  const getConfColor = (c: string) => {
    if (c === "High") return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
    if (c === "Medium") return "text-amber-500 bg-amber-500/10 border-amber-500/20";
    return "text-rose-500 bg-rose-500/10 border-rose-500/20";
  };

  const getRiskColor = (r: string) => {
    if (r === "Low") return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
    if (r === "Medium") return "text-amber-500 bg-amber-500/10 border-amber-500/20";
    return "text-rose-500 bg-rose-500/10 border-rose-500/20";
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <Card className="bg-card">
        <CardContent className="p-4 flex flex-col items-center text-center space-y-2">
          <Activity className="w-5 h-5 text-muted-foreground" />
          <p className="text-sm font-medium text-muted-foreground">Confidence</p>
          <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getConfColor(confidence)}`}>
            {confidence}
          </span>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardContent className="p-4 flex flex-col items-center text-center space-y-2">
          <ShieldAlert className="w-5 h-5 text-muted-foreground" />
          <p className="text-sm font-medium text-muted-foreground">Market Risk</p>
          <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getRiskColor(risk)}`}>
            {risk}
          </span>
        </CardContent>
      </Card>
    </div>
  );
}
