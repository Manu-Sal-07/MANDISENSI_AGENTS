import { Server, CheckCircle2 } from "lucide-react";

export function SystemStatusCard() {
  return (
    <div className="flex flex-col items-center justify-center space-y-2 mt-4">
      <div className="flex items-center space-x-2 text-xs font-medium text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-full border border-border">
        <Server className="w-3.5 h-3.5" />
        <span>System Health:</span>
        <span className="flex items-center text-emerald-500 gap-1"><CheckCircle2 className="w-3.5 h-3.5"/> All Systems Operational</span>
      </div>
      <p className="text-[10px] text-muted-foreground/70 uppercase tracking-widest">
        Last model retrain: Today at 04:00 AM
      </p>
    </div>
  );
}
