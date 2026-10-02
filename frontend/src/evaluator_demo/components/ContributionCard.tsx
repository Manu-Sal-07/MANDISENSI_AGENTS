import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

interface SubSignal {
  label: string;
  value: string;
}

interface ContributionCardProps {
  name: string;
  percentage: number;
  subSignals: SubSignal[];
  colorTheme: 'amber' | 'emerald' | 'violet';
}

export default function ContributionCard({
  name,
  percentage,
  subSignals,
  colorTheme,
}: ContributionCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Theme styling definitions
  const themeMap = {
    amber: {
      border: "border-amber-500/20 hover:border-amber-400/50",
      bg: "bg-amber-950/5",
      glow: "hover:shadow-[0_0_15px_rgba(245,158,11,0.1)]",
      text: "text-amber-400",
      percentageBg: "bg-amber-500/10 text-amber-400 border-amber-500/20"
    },
    emerald: {
      border: "border-emerald-500/20 hover:border-emerald-400/50",
      bg: "bg-emerald-950/5",
      glow: "hover:shadow-[0_0_15px_rgba(16,185,129,0.1)]",
      text: "text-emerald-400",
      percentageBg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
    },
    violet: {
      border: "border-violet-500/20 hover:border-violet-400/50",
      bg: "bg-violet-950/5",
      glow: "hover:shadow-[0_0_15px_rgba(139,92,246,0.1)]",
      text: "text-violet-400",
      percentageBg: "bg-violet-500/10 text-violet-400 border-violet-500/20"
    }
  };

  const currentTheme = themeMap[colorTheme];

  return (
    <div 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        border rounded-xl p-4 transition-[border-color,box-shadow,background-color] duration-300 bg-slate-950/90
        cursor-pointer relative overflow-hidden flex flex-col justify-between
        ${currentTheme.border} ${currentTheme.bg} ${currentTheme.glow}
      `}
    >
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">{name}</span>
          <span className="text-[9px] text-slate-500 mt-0.5 font-mono">WEIGHT_ATTRIBUTION</span>
        </div>
        
        <div className="flex items-center gap-3">
          <span className={`text-xs font-mono font-extrabold border px-2.5 py-0.5 rounded-full ${currentTheme.percentageBg}`}>
            {percentage}%
          </span>
          <motion.div 
            animate={{ rotate: isHovered ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          </motion.div>
        </div>
      </div>

      {/* Expandable sub-signals panel */}
      <AnimatePresence>
        {isHovered && (
          <motion.div 
            initial={{ height: 0, opacity: 0, marginTop: 0 }}
            animate={{ height: 'auto', opacity: 1, marginTop: 12 }}
            exit={{ height: 0, opacity: 0, marginTop: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="overflow-hidden border-t border-slate-900 pt-3"
          >
            <div className="space-y-1.5 font-mono text-[10px] text-slate-400">
              {subSignals.map((sig, idx) => (
                <div key={idx} className="flex justify-between items-center py-0.5">
                  <span>{sig.label}:</span>
                  <span className={`font-bold ${currentTheme.text}`}>{sig.value}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
