import { HeroPanel } from "@/components/dashboard/HeroPanel";
import { ChartPanel } from "@/components/dashboard/ChartPanel";
import { DriversPanel } from "@/components/dashboard/DriversPanel";
import { MarketPanel } from "@/components/dashboard/MarketPanel";
import { ActionsPanel } from "@/components/dashboard/ActionsPanel";

export function PremiumDashboard({ data, mockExtensions }: any) {
  const guidance = data.farmer_guidance;
  const attribution = data.attribution;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-[1600px] mx-auto w-full animate-in fade-in duration-700">
      {/* Hero Section */}
      <HeroPanel 
        decision={guidance.decision}
        priceMin={guidance.price_range.min}
        priceMax={guidance.price_range.max}
        confidence={guidance.confidence_label}
        risk={guidance.risk_label}
      />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Intelligence */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <ChartPanel 
            currentPrice={mockExtensions.price_now}
            predictedPrice={guidance.price_range.max}
          />
          <DriversPanel 
            supply={attribution.arrival_pct}
            demand={attribution.external_pct}
            weather={-15} // Mock weather impact
            seasonality={attribution.seasonality_pct}
          />
        </div>

        {/* Right Column: Status & Actions */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <MarketPanel 
            arrivals={mockExtensions.price_now > 35 ? "High" : "Medium"}
            demand="Strong"
            trend={guidance.decision === "SELL" ? "Downward" : "Upward"}
          />
          <ActionsPanel />
        </div>
      </div>
    </div>
  );
}
