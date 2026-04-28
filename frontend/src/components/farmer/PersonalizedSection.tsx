"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calculator, IndianRupee, AlertTriangle, Lightbulb, Scale } from "lucide-react";

interface PersonalizedSectionProps {
  priceNow: number;
  priceFuture: number;
}

export function PersonalizedSection({ priceNow, priceFuture }: PersonalizedSectionProps) {
  const [quantity, setQuantity] = useState<number>(1000);
  const [urgency, setUrgency] = useState<"Low" | "Medium" | "High">("High");
  const [canStore, setCanStore] = useState<boolean>(false);
  const [offeredPrice, setOfferedPrice] = useState<number>(priceNow);

  // Derived calculations
  const earningsNow = quantity * priceNow;
  const earningsFuture = quantity * priceFuture;
  const isUnderpaid = offeredPrice < priceNow;

  return (
    <div className="space-y-6">
      
      {/* 1. INPUT CARD */}
      <Card className="bg-card border-primary/20 shadow-sm shadow-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2 text-foreground">
            <Calculator className="w-5 h-5 text-primary" />
            Your Situation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 mt-2">
          
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-muted-foreground">Quantity to sell (kg)</label>
            <input 
              type="number" 
              value={quantity} 
              onChange={(e) => setQuantity(Number(e.target.value) || 0)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-muted-foreground">Need cash urgently?</label>
            <div className="flex gap-2">
              {["Low", "Medium", "High"].map((u) => (
                <button
                  key={u}
                  onClick={() => setUrgency(u as any)}
                  className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${urgency === u ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-muted-foreground">Can you store it safely?</label>
            <div className="flex gap-2">
              <button
                onClick={() => setCanStore(true)}
                className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${canStore ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`}
              >
                Yes
              </button>
              <button
                onClick={() => setCanStore(false)}
                className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${!canStore ? 'bg-rose-500 text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`}
              >
                No
              </button>
            </div>
          </div>

        </CardContent>
      </Card>

      {/* 2. EARNINGS CALCULATOR CARD */}
      <Card className="bg-card">
        <CardContent className="p-0">
          <div className="flex divide-x divide-border">
            <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-1 bg-emerald-500/5">
              <span className="text-sm font-bold text-foreground">Sell Now</span>
              <span className="text-xl font-bold text-emerald-500">₹{earningsNow.toLocaleString()}</span>
            </div>
            <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-1 bg-amber-500/5">
              <span className="text-sm font-bold text-foreground">Wait</span>
              <span className="text-xl font-bold text-amber-500">₹{earningsFuture.toLocaleString()}</span>
              <span className="text-xs text-amber-500/80">(risk)</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. CONTEXT-AWARE RECOMMENDATION */}
      <Card className="bg-card border-primary/50">
        <CardContent className="p-4 flex items-start gap-3 bg-primary/5">
          <Lightbulb className="w-6 h-6 text-primary shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">
              Because urgency is <span className="font-bold text-foreground uppercase">{urgency}</span>
              {!canStore && " and you CANNOT store"}...
            </p>
            <p className="text-lg font-black text-foreground">
              → {urgency === "High" || !canStore ? "SELL NOW" : "WAIT"} recommended
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 4. FAIR PRICE CHECK CARD */}
      <Card className="bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2 text-foreground">
            <Scale className="w-5 h-5 text-primary" />
            Fair Price Check
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 mt-2">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-muted-foreground">What price are you being offered? (₹/kg)</label>
            <div className="relative">
              <IndianRupee className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input 
                type="number" 
                value={offeredPrice} 
                onChange={(e) => setOfferedPrice(Number(e.target.value) || 0)}
                className="w-full bg-background border border-border rounded-md pl-9 pr-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
          </div>

          {isUnderpaid ? (
            <div className="flex items-start gap-2 p-3 bg-rose-500/10 text-rose-500 rounded-lg border border-rose-500/20">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="text-sm font-medium">
                Warning: You are being underpaid. The fair market price today is at least ₹{priceNow}/kg.
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2 p-3 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20">
              <Calculator className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="text-sm font-medium">
                Good offer. This is at or above the fair market price of ₹{priceNow}/kg.
              </div>
            </div>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
