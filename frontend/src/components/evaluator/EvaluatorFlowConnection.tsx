'use client';

import React from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

interface EvaluatorFlowConnectionProps {
  accentColor?: 'cyan' | 'emerald' | 'violet' | 'amber';
}

export default function EvaluatorFlowConnection({
  accentColor = 'cyan',
}: EvaluatorFlowConnectionProps) {
  const colorMap = {
    cyan: 'text-cyan-500/40 group-hover:text-cyan-400',
    emerald: 'text-emerald-500/40 group-hover:text-emerald-400',
    violet: 'text-violet-500/40 group-hover:text-violet-400',
    amber: 'text-amber-500/40 group-hover:text-amber-400',
  };

  const lineColors = {
    cyan: 'from-cyan-500/20 to-transparent',
    emerald: 'from-emerald-500/20 to-transparent',
    violet: 'from-violet-500/20 to-transparent',
    amber: 'from-amber-500/20 to-transparent',
  };

  const currentLine = lineColors[accentColor];
  const currentColor = colorMap[accentColor];

  return (
    <div className="flex items-center justify-center group py-2 md:py-0 md:px-1 select-none">
      {/* 1. Desktop Mode (Horizontal Connector) */}
      <div className="hidden md:flex items-center gap-1.5 w-10">
        <div className={`h-[1px] w-6 bg-gradient-to-r ${currentLine}`} />
        <ChevronRight className={`w-4 h-4 transition-colors duration-300 ${currentColor}`} />
      </div>

      {/* 2. Mobile Mode (Vertical Connector) */}
      <div className="flex md:hidden flex-col items-center gap-1.5 h-8">
        <div className={`w-[1px] h-4 bg-gradient-to-b ${currentLine}`} />
        <ChevronDown className={`w-4 h-4 transition-colors duration-300 ${currentColor}`} />
      </div>
    </div>
  );
}
