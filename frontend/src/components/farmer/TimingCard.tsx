import { Card, CardContent } from "@/components/ui/card";
import { Calendar, AlertTriangle } from "lucide-react";

interface TimingCardProps {
  bestTime: string;
  avoidAfter: string;
}

export function TimingCard({ bestTime, avoidAfter }: TimingCardProps) {
  return (
    <Card className="bg-card">
      <CardContent className="p-0 divide-y divide-border">
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Calendar className="w-5 h-5 text-emerald-500" />
            <span className="font-medium text-foreground">Best Time</span>
          </div>
          <span className="font-bold text-emerald-500">{bestTime}</span>
        </div>
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-500" />
            <span className="font-medium text-foreground">Avoid</span>
          </div>
          <span className="font-bold text-rose-500">after {avoidAfter}</span>
        </div>
      </CardContent>
    </Card>
  );
}
