"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, MessageSquareHeart } from "lucide-react";

export function FeedbackCard() {
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <Card className="bg-emerald-500/10 border-emerald-500/20">
        <CardContent className="p-4 flex flex-col items-center justify-center text-center space-y-2">
          <MessageSquareHeart className="w-6 h-6 text-emerald-500" />
          <p className="text-sm font-medium text-emerald-500">Thank you for your feedback! This helps us improve.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card">
      <CardContent className="p-4 flex flex-col items-center text-center space-y-4">
        <p className="text-sm font-medium text-foreground">Was this recommendation helpful?</p>
        <div className="flex gap-4 w-full">
          <Button 
            variant="outline" 
            className="flex-1 border-emerald-500/50 hover:bg-emerald-500/10 hover:text-emerald-500"
            onClick={() => setSubmitted(true)}
          >
            <ThumbsUp className="w-4 h-4 mr-2" /> Yes
          </Button>
          <Button 
            variant="outline" 
            className="flex-1 border-rose-500/50 hover:bg-rose-500/10 hover:text-rose-500"
            onClick={() => setSubmitted(true)}
          >
            <ThumbsDown className="w-4 h-4 mr-2" /> No
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
