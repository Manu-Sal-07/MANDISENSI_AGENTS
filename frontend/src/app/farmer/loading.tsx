import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex flex-col min-h-screen bg-background items-center justify-center">
      <div className="flex flex-col items-center space-y-4 text-primary">
        <Loader2 className="w-10 h-10 animate-spin" />
        <h2 className="text-lg font-semibold tracking-tight">Analyzing market signals...</h2>
      </div>
    </div>
  );
}
