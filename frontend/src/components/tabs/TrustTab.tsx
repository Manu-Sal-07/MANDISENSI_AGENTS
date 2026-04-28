import { AccuracyCard } from "@/components/farmer/AccuracyCard";
import { PredictionVsActualCard } from "@/components/farmer/PredictionVsActualCard";
import { SystemStatusCard } from "@/components/farmer/SystemStatusCard";
import { FeedbackCard } from "@/components/farmer/FeedbackCard";

export function TrustTab({ accuracy, lastPrediction }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 h-full max-w-7xl mx-auto">
      <div className="flex flex-col gap-4">
        <AccuracyCard overall={accuracy} />
      </div>
      <div className="flex flex-col gap-4 h-full">
        <PredictionVsActualCard predicted={lastPrediction.predicted} actual={lastPrediction.actual} />
      </div>
      <div className="flex flex-col gap-4">
        <SystemStatusCard />
        <FeedbackCard />
      </div>
    </div>
  );
}
