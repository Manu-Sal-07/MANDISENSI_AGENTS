import React from 'react';

type SignalTheme = 'amber' | 'emerald' | 'violet';

interface SignalPacketProps {
  label: string;
  theme: SignalTheme;
  className?: string;
}

export default function SignalPacket({ label, theme, className = '' }: SignalPacketProps) {
  const themeMap = {
    amber: "border-amber-500/40 bg-amber-950/60 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)]",
    emerald: "border-emerald-500/40 bg-emerald-950/60 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]",
    violet: "border-violet-500/40 bg-violet-950/60 text-violet-300 shadow-[0_0_12px_rgba(139,92,246,0.3)]"
  };

  return (
    <span 
      className={`
        px-2.5 py-1 rounded-full border text-[9px] font-bold font-mono uppercase tracking-wide
        flex items-center justify-center whitespace-nowrap ${themeMap[theme]} ${className}
      `}
    >
      {label}
    </span>
  );
}
