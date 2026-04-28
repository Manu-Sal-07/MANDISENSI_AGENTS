"use client";

import { OpportunityCard, OpportunityData } from "./OpportunityCard";

interface OpportunityGridProps {
  opportunities: OpportunityData[];
}

export function OpportunityGrid({ opportunities }: OpportunityGridProps) {
  if (!opportunities || opportunities.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 border border-dashed rounded-lg border-border/50 bg-card/20">
        <p className="text-muted-foreground">No opportunities currently detected.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {opportunities.map((opp, index) => (
        <OpportunityCard key={opp.id} data={opp} index={index} />
      ))}
    </div>
  );
}
