import { fetchPrediction } from "@/lib/api";
import { SimpleDecision } from "@/components/farmer/simple/SimpleDecision";
import { VoiceButton } from "@/components/farmer/simple/VoiceButton";
import { Feedback } from "@/components/farmer/simple/Feedback";
import { buttonVariants } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

// Prevent Next.js from aggressively caching this page to ensure live data
export const revalidate = 0;

export default async function SimpleFarmerPage() {
  // Fetch real prediction from the FastAPI backend
  // For this simple view, we hardcode tomato/kolar as an example
  const data = await fetchPrediction("tomato", "kolar");
  
  const guidance = data.farmer_guidance;

  return (
    <div className="flex flex-col min-h-[100dvh] bg-background text-foreground">
      
      {/* Minimal Header */}
      <header className="flex items-center p-4">
        <Link href="/farmer" className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "rounded-full")}>
          <ArrowLeft className="w-6 h-6" />
          <span className="sr-only">Back</span>
        </Link>
        <span className="font-bold text-lg ml-2 opacity-80">Tomato (Kolar)</span>
      </header>

      {/* Main Single-Screen Content */}
      <main className="flex-1 flex flex-col justify-center max-w-sm w-full mx-auto px-6 pb-12 space-y-8">
        
        <SimpleDecision 
          decision={guidance.decision}
          priceMin={guidance.price_range.min}
          priceMax={guidance.price_range.max}
          confidence={guidance.confidence_label}
          risk={guidance.risk_label}
        />

        <VoiceButton 
          decision={guidance.decision}
          priceMin={guidance.price_range.min}
          priceMax={guidance.price_range.max}
        />

        <Feedback />

      </main>
    </div>
  );
}
