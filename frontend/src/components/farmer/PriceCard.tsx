import { Card, CardContent } from "@/components/ui/card";
import { IndianRupee } from "lucide-react";

interface PriceCardProps {
  minPrice: number;
  maxPrice: number;
}

export function PriceCard({ minPrice, maxPrice }: PriceCardProps) {
  return (
    <Card className="bg-card">
      <CardContent className="p-6 flex flex-col items-center text-center space-y-2">
        <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
          Expected Price (Next 7 Days)
        </p>
        <div className="flex items-center justify-center space-x-1 text-3xl sm:text-4xl font-bold text-foreground">
          <IndianRupee className="w-6 h-6 sm:w-8 sm:h-8" />
          <span>{minPrice}</span>
          <span className="text-muted-foreground font-normal mx-2">–</span>
          <IndianRupee className="w-6 h-6 sm:w-8 sm:h-8" />
          <span>{maxPrice}</span>
        </div>
      </CardContent>
    </Card>
  );
}
