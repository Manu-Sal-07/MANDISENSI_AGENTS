import React from 'react';

interface DataPacketProps {
  label: string;
  className?: string;
}

export default function DataPacket({ label, className = '' }: DataPacketProps) {
  return (
    <span 
      className={`
        px-2.5 py-1 rounded-full border border-sky-400/35 bg-sky-950/50 
        text-sky-300 font-mono text-[9px] font-bold uppercase tracking-wider 
        shadow-[0_0_10px_rgba(56,189,248,0.25)] flex items-center justify-center 
        whitespace-nowrap animate-pulse ${className}
      `}
    >
      {label}
    </span>
  );
}
