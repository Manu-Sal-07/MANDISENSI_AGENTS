import { Loader2 } from "lucide-react";
import { UI_TEXT } from "@/components/farmer/simple/content";

export default function Loading() {
  return (
    <div className="flex flex-col min-h-[100dvh] bg-background items-center justify-center p-6">
      <div className="flex flex-col items-center space-y-6 text-primary">
        <Loader2 className="w-16 h-16 animate-spin" />
        <h2 className="text-2xl font-black tracking-tight text-center px-4">{UI_TEXT.errors.loading}</h2>
      </div>
    </div>
  );
}
