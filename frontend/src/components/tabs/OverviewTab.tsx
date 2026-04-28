import { ChartCard } from "@/components/dashboard/ChartCard";
import { DriversCard } from "@/components/dashboard/DriversCard";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { WhyCard } from "@/components/farmer/WhyCard";
import { TimingCard } from "@/components/farmer/TimingCard";

interface OverviewTabProps {
  explanations: string[];
  bestTime: string;
  avoidAfter: string;
  priceNow: number;
  data: any;
}

export function OverviewTab({ explanations, bestTime, avoidAfter, priceNow, data }: OverviewTabProps) {
  const predicted = data.farmer_guidance.price_range.max;
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 animate-in slide-in-from-bottom-4 duration-500 h-full max-w-7xl mx-auto">
      
      {/* Column 1: Core Metrics & Actions */}
      <div className="flex flex-col gap-4">
        <ChartCard currentPrice={priceNow} predictedPrice={predicted} />
        <QuickActions />
      </div>
      
      {/* Column 2: Market Drivers */}
      <div className="flex flex-col gap-4 h-full">
        <DriversCard 
          supplyImpact={data.attribution.arrival_pct} 
          demandImpact={data.attribution.external_pct} 
          seasonality={data.attribution.seasonality_pct} 
        />
      </div>

      {/* Column 3: Insights & Timing */}
      <div className="flex flex-col gap-4">
        <WhyCard reasons={explanations} />
        <TimingCard bestTime={bestTime} avoidAfter={avoidAfter} />
      </div>

    </div>
  );
}
