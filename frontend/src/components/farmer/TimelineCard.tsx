import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock } from "lucide-react";

export function TimelineCard() {
  const events = [
    { day: "Day 1", event: "Supply drop" },
    { day: "Day 2", event: "Demand increase" },
    { day: "Day 3", event: "Price rising" },
  ];

  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <Clock className="w-5 h-5 text-primary" />
          Signal Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="mt-2">
        <div className="relative border-l-2 border-primary/20 ml-3 space-y-4">
          {events.map((e, i) => (
            <div key={i} className="relative pl-5">
              {/* Dot */}
              <div className={`absolute -left-[5px] top-1.5 w-2 h-2 rounded-full ${i === events.length - 1 ? 'bg-primary ring-4 ring-primary/20' : 'bg-muted-foreground'}`} />
              <p className="text-xs font-bold text-muted-foreground uppercase">{e.day}</p>
              <p className={`text-sm font-medium ${i === events.length - 1 ? 'text-foreground font-bold' : 'text-foreground/80'}`}>{e.event}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
