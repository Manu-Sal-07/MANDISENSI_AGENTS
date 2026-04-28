"use client";

import { useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

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
    <div className="flex flex-col min-h-screen bg-background text-foreground pb-8">
      <header className="sticky top-0 z-10 flex items-center justify-between p-4 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/" className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "rounded-full")}>
            <ArrowLeft className="w-5 h-5" />
            <span className="sr-only">Back</span>
          </Link>
          <h1 className="text-xl font-bold tracking-tight">Onion Market</h1>
        </div>
      </header>

      <main className="flex-1 w-full max-w-md mx-auto px-4 py-12 flex flex-col items-center justify-center space-y-6">
        <Card className="bg-rose-500/10 border-rose-500/20 text-rose-500 w-full">
          <CardContent className="p-6 flex flex-col items-center text-center space-y-4">
            <AlertCircle className="w-10 h-10" />
            <div className="space-y-1">
              <h2 className="text-lg font-bold">Could not load market data</h2>
              <p className="text-sm font-medium opacity-80">Our AI systems are currently unavailable or there was a connection error.</p>
            </div>
            <Button 
              variant="outline" 
              className="mt-4 border-rose-500/50 hover:bg-rose-500/20 hover:text-rose-500"
              onClick={() => reset()}
            >
              Try Again
            </Button>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
