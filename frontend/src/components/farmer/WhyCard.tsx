import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle, ChevronRight } from "lucide-react";

interface WhyCardProps {
  reasons: string[];
}

export function WhyCard({ reasons }: WhyCardProps) {
  return (
    <Card className="bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2 text-foreground">
          <HelpCircle className="w-5 h-5 text-primary" />
          Why?
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3 mt-2">
          {reasons.map((reason, index) => (
            <li key={index} className="flex items-start gap-3">
              <ChevronRight className="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
              <span className="text-foreground font-medium">{reason}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
