import { DailyAdviceCard } from "@/components/farmer/DailyAdviceCard";
import { AlertsCard } from "@/components/farmer/AlertsCard";
import { WhatChangedCard } from "@/components/farmer/WhatChangedCard";
import { TimelineCard } from "@/components/farmer/TimelineCard";

export function AlertsTab({ alerts, changes }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 h-full max-w-7xl mx-auto">
      <div className="flex flex-col gap-4">
        <DailyAdviceCard />
        <AlertsCard alerts={alerts} />
      </div>
      <div className="flex flex-col gap-4 h-full">
        <WhatChangedCard changeContext={changes} />
      </div>
      <div className="flex flex-col gap-4">
        <TimelineCard />
      </div>
    </div>
  );
}
