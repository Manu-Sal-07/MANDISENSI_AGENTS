import { Card, CardContent } from "@/components/ui/card";
import { History, Frown } from "lucide-react";

export function HistoryCard() {
  return (
    <Card className="bg-card border-amber-500/20 shadow-sm shadow-amber-500/5">
      <CardContent className="p-4 flex flex-col space-y-2">
        <div className="flex items-center gap-2 text-amber-500">
          <History className="w-4 h-4" />
          <span className="text-sm font-bold uppercase tracking-wide">Last Decision</span>
        </div>
        <div className="flex items-start gap-2 bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-sm">
          <Frown className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-amber-500 font-medium">You waited → price dropped</p>
        </div>
      </CardContent>
    </Card>
  );
}
