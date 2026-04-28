"use client";

import { useState } from "react";
import { UI_TEXT } from "./content";
import { Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VoiceButtonProps {
  decision: string;
  priceMin: number;
  priceMax: number;
}

export function VoiceButton({ decision, priceMin, priceMax }: VoiceButtonProps) {
  const [isPlaying, setIsPlaying] = useState(false);

  const handleSpeak = () => {
    if (!('speechSynthesis' in window)) {
      alert("Voice not supported on this browser.");
      return;
    }

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }

    const textToRead = `${decision} now. Expected price is between ${priceMin} and ${priceMax} rupees.`;
    const utterance = new SpeechSynthesisUtterance(textToRead);
    
    // Optional: try to find a local language voice
    // const voices = window.speechSynthesis.getVoices();
    // const localVoice = voices.find(v => v.lang.includes('en-IN') || v.lang.includes('hi-IN'));
    // if (localVoice) utterance.voice = localVoice;

    utterance.onend = () => setIsPlaying(false);
    
    setIsPlaying(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <Button 
      variant="outline" 
      size="lg" 
      className="w-full py-8 text-xl font-bold rounded-xl border-2 hover:bg-primary/5 active:scale-95 transition-all"
      onClick={handleSpeak}
    >
      {isPlaying ? (
        <><VolumeX className="w-6 h-6 mr-3 text-rose-500" /> {UI_TEXT.voice.stop}</>
      ) : (
        <><Volume2 className="w-6 h-6 mr-3 text-primary" /> {UI_TEXT.voice.listen}</>
      )}
    </Button>
  );
}
