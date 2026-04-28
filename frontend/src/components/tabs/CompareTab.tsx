import { DecisionComparisonCard } from "@/components/farmer/DecisionComparisonCard";
import { RegretCard } from "@/components/farmer/RegretCard";
import { ProbabilityCard } from "@/components/farmer/ProbabilityCard";

export function CompareTab({ sell, wait, decision }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 h-full max-w-7xl mx-auto">
      <div className="flex flex-col gap-4">
        <DecisionComparisonCard sell={sell} wait={wait} />
      </div>
      <div className="flex flex-col gap-4 h-full">
        <RegretCard sell_loss={2} wait_loss={5} />
      </div>
      <div className="flex flex-col gap-4">
        <ProbabilityCard 
          sell_prob={decision === "SELL" ? 80 : 40} 
          wait_prob={decision === "WAIT" ? 70 : 30} 
        />
      </div>
    </div>
  );
}
