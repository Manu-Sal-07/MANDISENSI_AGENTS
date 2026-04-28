import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, ArrowRight } from "lucide-react";

interface WhatChangedCardProps {
  changeContext: string;
}

export function WhatChangedCard({ changeContext }: WhatChangedCardProps) {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <RefreshCw className="w-5 h-5 text-primary" />
          What Changed Today
        </CardTitle>
      </CardHeader>
      <CardContent className="mt-2">
        <div className="flex flex-col gap-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
          <span className="text-sm font-medium text-muted-foreground">{changeContext}</span>
          <div className="flex items-center gap-2 text-foreground font-bold">
            <ArrowRight className="w-4 h-4 text-emerald-500" />
            Price rising
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
