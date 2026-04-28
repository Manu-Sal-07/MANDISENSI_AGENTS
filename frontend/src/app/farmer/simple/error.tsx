"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UI_TEXT } from "@/components/farmer/simple/content";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col min-h-[100dvh] bg-background items-center justify-center p-6">
      <div className="w-full max-w-sm flex flex-col items-center text-center space-y-8 bg-rose-500/5 p-8 rounded-3xl border-2 border-rose-500/20">
        <AlertCircle className="w-20 h-20 text-rose-500" />
        <div className="space-y-2">
          <h2 className="text-2xl font-black text-rose-500">{UI_TEXT.errors.fallback}</h2>
          <p className="text-lg font-medium text-muted-foreground">Unable to connect to the network.</p>
        </div>
        <Button 
          size="lg" 
          className="w-full h-16 text-xl font-bold rounded-xl"
          onClick={() => reset()}
        >
          {UI_TEXT.errors.tryAgain}
        </Button>
      </div>
    </div>
  );
}
