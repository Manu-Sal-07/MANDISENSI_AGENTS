import { CheckCircle, Clock } from "lucide-react";

interface TrustCardProps {
  accuracy: number;
  updated: string;
}

export function TrustCard({ accuracy, updated }: TrustCardProps) {
  return (
    <div className="flex flex-col items-center justify-center space-y-2 mt-4 opacity-70">
      <div className="flex items-center space-x-4 text-xs font-medium text-muted-foreground">
        <div className="flex items-center space-x-1">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>System Accuracy: {accuracy}%</span>
        </div>
        <div className="flex items-center space-x-1">
          <Clock className="w-3.5 h-3.5" />
          <span>Updated {updated}</span>
        </div>
      </div>
    </div>
  );
}
