import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart2 } from "lucide-react";

interface AccuracyCardProps {
  overall: number;
}

export function AccuracyCard({ overall }: AccuracyCardProps) {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <BarChart2 className="w-5 h-5 text-primary" />
          AI Accuracy Record
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 mt-2">
        <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg border border-border">
          <span className="text-3xl font-black text-foreground">{overall}%</span>
          <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Overall Accuracy</span>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-foreground">Tomato Predictions</span>
            <span className="font-bold text-emerald-500">76%</span>
          </div>
          <div className="flex justify-between items-center text-sm">
            <span className="text-foreground">Onion Predictions</span>
            <span className="font-bold text-emerald-500">72%</span>
          </div>
          <div className="flex justify-between items-center text-sm">
            <span className="text-foreground">Potato Predictions</span>
            <span className="font-bold text-amber-500">64%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
