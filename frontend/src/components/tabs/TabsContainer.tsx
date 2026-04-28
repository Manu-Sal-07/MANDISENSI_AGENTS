"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewTab } from "./OverviewTab";
import { CompareTab } from "./CompareTab";
import { PersonalTab } from "./PersonalTab";
import { AlertsTab } from "./AlertsTab";
import { TrustTab } from "./TrustTab";
import { Home, Scale, User, Bell, ShieldCheck } from "lucide-react";

const TabItem = ({ value, icon: Icon, label }: { value: string, icon: any, label: string }) => (
  <TabsTrigger 
    value={value} 
    className="flex items-center gap-2 rounded-full px-5 py-2.5 font-bold text-sm tracking-wide data-[state=active]:bg-emerald-500/15 data-[state=active]:text-emerald-500 data-[state=active]:border-emerald-500/50 border border-transparent transition-all data-[state=active]:shadow-[0_0_15px_rgba(34,197,94,0.15)] hover:bg-slate-800/50"
  >
    <Icon className="w-4 h-4" />
    {label}
  </TabsTrigger>
);

export function TabsContainer({ data, mockExtensions }: any) {
  const guidance = data.farmer_guidance;

  return (
    <Tabs defaultValue="overview" className="flex-1 flex flex-col w-full h-full overflow-hidden mt-2">
      <div className="flex-none bg-background/95 backdrop-blur-md z-10 border-b border-border shadow-md w-full">
        <div className="max-w-7xl mx-auto w-full px-4 pt-2 pb-3">
          <TabsList className="flex w-full justify-start h-auto bg-transparent overflow-x-auto no-scrollbar gap-2 p-0">
            <TabItem value="overview" icon={Home} label="Overview" />
            <TabItem value="compare" icon={Scale} label="Compare" />
            <TabItem value="personal" icon={User} label="Personal" />
            <TabItem value="alerts" icon={Bell} label="Alerts" />
            <TabItem value="trust" icon={ShieldCheck} label="Trust" />
          </TabsList>
        </div>
      </div>

      <div className="flex-1 relative overflow-y-auto bg-slate-950/50 p-4 pb-24 no-scrollbar">
        <TabsContent value="overview" className="m-0 h-full outline-none">
          <OverviewTab 
            data={data}
            explanations={guidance.explanation} 
            bestTime={guidance.decision === "SELL" ? "Today" : "Wait 7 days"} 
            avoidAfter="7 days" 
            priceNow={mockExtensions.price_now}
          />
        </TabsContent>
        
        <TabsContent value="compare" className="m-0 h-full outline-none">
          <CompareTab 
            decision={guidance.decision}
            sell={{ min: mockExtensions.price_now * 0.98, max: mockExtensions.price_now * 1.02, safe: guidance.decision === "SELL" }} 
            wait={{ expected: guidance.price_range.max, risk_price: guidance.price_range.min }} 
          />
        </TabsContent>
        
        <TabsContent value="personal" className="m-0 h-full outline-none">
          <PersonalTab 
            priceNow={mockExtensions.price_now} 
            priceFuture={guidance.price_range.max} 
            mandis={mockExtensions.mandis} 
          />
        </TabsContent>
        
        <TabsContent value="alerts" className="m-0 h-full outline-none">
          <AlertsTab 
            alerts={mockExtensions.alerts} 
            changes={mockExtensions.changes} 
          />
        </TabsContent>
        
        <TabsContent value="trust" className="m-0 h-full outline-none">
          <TrustTab 
            accuracy={mockExtensions.accuracy} 
            lastPrediction={mockExtensions.last_prediction} 
          />
        </TabsContent>
      </div>
    </Tabs>
  );
}
