import React from 'react';
import { Loader2, Check } from 'lucide-react';

export type NodeState = 'idle' | 'running' | 'completed';

interface NodeStatusIndicatorProps {
  state: NodeState;
}

export default function NodeStatusIndicator({ state }: NodeStatusIndicatorProps) {
  if (state === 'completed') {
    return (
      <div className="w-7 h-7 rounded-full bg-emerald-950/60 border border-emerald-500 flex items-center justify-center shadow-[0_0_10px_rgba(52,211,153,0.3)] animate-[scaleIn_0.2s_ease-out_both]">
        <Check className="w-3.5 h-3.5 text-emerald-400" />
      </div>
    );
  }

  if (state === 'running') {
    return (
      <div className="relative w-7 h-7 rounded-full bg-sky-950/65 border border-sky-400 flex items-center justify-center shadow-[0_0_12px_rgba(56,189,248,0.35)]">
        <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />
        <div className="absolute inset-0 rounded-full border border-sky-400 animate-ping opacity-30" />
      </div>
    );
  }

  // Idle state
  return (
    <div className="w-7 h-7 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center">
      <div className="w-2 h-2 rounded-full bg-slate-700" />
    </div>
  );
}
