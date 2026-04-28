"use client";

import { useState } from "react";
import { UI_TEXT } from "./content";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, MessageSquareHeart } from "lucide-react";

export function Feedback() {
  const [step, setStep] = useState<"initial" | "negative_reasons" | "done">("initial");

  const handleYes = () => {
    // Fire analytics event here
    setStep("done");
  };

  const handleNo = () => {
    setStep("negative_reasons");
  };

  const handleReason = (reason: string) => {
    // Fire analytics event here with the reason
    setStep("done");
  };

  if (step === "done") {
    return (
      <div className="w-full p-6 mt-4 rounded-xl bg-emerald-500/10 border-2 border-emerald-500/20 text-center animate-in fade-in zoom-in duration-300">
        <MessageSquareHeart className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
        <p className="text-lg font-bold text-emerald-500">{UI_TEXT.feedback.thanks}</p>
      </div>
    );
  }

  if (step === "negative_reasons") {
    return (
      <div className="w-full space-y-3 mt-4 animate-in slide-in-from-right-4 duration-300">
        <p className="text-center font-semibold text-muted-foreground mb-4">What was wrong?</p>
        <Button variant="outline" size="lg" className="w-full justify-start text-lg h-14" onClick={() => handleReason("wrongTiming")}>
          ⏱️ {UI_TEXT.feedback.wrongTiming}
        </Button>
        <Button variant="outline" size="lg" className="w-full justify-start text-lg h-14" onClick={() => handleReason("wrongPrice")}>
          💰 {UI_TEXT.feedback.wrongPrice}
        </Button>
        <Button variant="outline" size="lg" className="w-full justify-start text-lg h-14" onClick={() => handleReason("confusing")}>
          🤔 {UI_TEXT.feedback.confusing}
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4 mt-4">
      <p className="text-center text-lg font-bold text-foreground opacity-80">{UI_TEXT.feedback.question}</p>
      <div className="flex gap-4">
        <Button 
          variant="outline" 
          size="lg"
          className="flex-1 h-16 text-2xl font-bold border-2 border-border hover:bg-emerald-500/10 hover:text-emerald-500 hover:border-emerald-500/50 transition-colors"
          onClick={handleYes}
        >
          👍 {UI_TEXT.feedback.yes}
        </Button>
        <Button 
          variant="outline" 
          size="lg"
          className="flex-1 h-16 text-2xl font-bold border-2 border-border hover:bg-rose-500/10 hover:text-rose-500 hover:border-rose-500/50 transition-colors"
          onClick={handleNo}
        >
          👎 {UI_TEXT.feedback.no}
        </Button>
      </div>
    </div>
  );
}
