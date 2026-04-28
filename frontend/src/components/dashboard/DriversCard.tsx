"use client";

import { MetricCard } from "./MetricCard";
import { Activity } from "lucide-react";

const DriverBar = ({ label, value }: { label: string, value: number }) => {
  const isPositive = value >= 0;
  const width = Math.abs(value);
  const color = isPositive ? "bg-emerald-500" : "bg-rose-500";
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-semibold">
        <span className="text-muted-foreground">{label}</span>
        <span className={isPositive ? "text-emerald-500" : "text-rose-500"}>
          {isPositive ? "+" : ""}{value.toFixed(0)}%
        </span>
      </div>
      <div className="flex h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
        {/* If negative, push from middle to left. If positive, push from middle to right. */}
        <div className="w-1/2 flex justify-end pr-0.5">
          {!isPositive && <div className={`h-full ${color} rounded-l-full`} style={{ width: `${width}%` }} />}
        </div>
        <div className="w-1/2 flex justify-start pl-0.5">
          {isPositive && <div className={`h-full ${color} rounded-r-full`} style={{ width: `${width}%` }} />}
        </div>
      </div>
    </div>
  );
};

interface DriversCardProps {
  supplyImpact: number; // -100 to 100
  demandImpact: number; // -100 to 100
  seasonality: number;  // -100 to 100
}

export function DriversCard({ supplyImpact, demandImpact, seasonality }: DriversCardProps) {

  return (
    <MetricCard title="Key Market Drivers" icon={<Activity className="w-4 h-4" />}>
      <div className="space-y-4 py-2">
        <DriverBar label="Arrival Volume (Supply)" value={supplyImpact} />
        <DriverBar label="External Factors (Demand)" value={demandImpact} />
        <DriverBar label="Historical Seasonality" value={seasonality} />
      </div>
    </MetricCard>
  );
}
