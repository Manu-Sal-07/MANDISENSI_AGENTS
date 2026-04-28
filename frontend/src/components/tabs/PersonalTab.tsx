import { PersonalizedSection } from "@/components/farmer/PersonalizedSection";
import { MarketCard } from "@/components/farmer/MarketCard";
import { StorageCard } from "@/components/farmer/StorageCard";

export function PersonalTab({ priceNow, priceFuture, mandis }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 h-full max-w-7xl mx-auto">
      <div className="flex flex-col gap-4">
        <PersonalizedSection priceNow={priceNow} priceFuture={priceFuture} />
      </div>
      <div className="flex flex-col gap-4 h-full">
        <MarketCard mandis={mandis} />
      </div>
      <div className="flex flex-col gap-4">
        <StorageCard />
      </div>
    </div>
  );
}
