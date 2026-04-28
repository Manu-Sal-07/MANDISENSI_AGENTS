import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MapPin, Trophy } from "lucide-react";

interface Mandi {
  name: string;
  price: number;
}

interface MarketCardProps {
  mandis: Mandi[];
}

export function MarketCard({ mandis }: MarketCardProps) {
  // Find the best market (highest price)
  const bestMandi = mandis.reduce((prev, current) => (prev.price > current.price) ? prev : current);

  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <MapPin className="w-5 h-5 text-primary" />
          Nearby Markets
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 mt-2">
        {mandis.map((mandi, index) => {
          const isBest = mandi.name === bestMandi.name;
          return (
            <div 
              key={index} 
              className={`flex items-center justify-between p-3 rounded-lg border ${isBest ? 'border-emerald-500 bg-emerald-500/10' : 'border-border bg-background'}`}
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">{mandi.name}</span>
                {isBest && <Trophy className="w-4 h-4 text-emerald-500" />}
              </div>
              <span className={`font-bold ${isBest ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                ₹{mandi.price} / kg
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
