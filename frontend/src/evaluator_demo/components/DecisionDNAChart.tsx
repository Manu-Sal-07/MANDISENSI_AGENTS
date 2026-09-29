import React from 'react';
import { motion } from 'framer-motion';

interface DecisionDNAChartProps {
  progress: number; // 0 to 100
  dna?: {
    arrival: number;
    seasonality: number;
    external: number;
  };
}

export default function DecisionDNAChart({ progress, dna }: DecisionDNAChartProps) {
  // Donut animation range: progress 45 to 65
  const startProgress = 45;
  const endProgress = 65;
  const ratio = Math.min(Math.max((progress - startProgress) / (endProgress - startProgress), 0), 1);

  // SVG Circle Parameters
  const radius = 50;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius; // ~314.159

  // Target values
  const values = dna || {
    arrival: 0.46,
    seasonality: 0.38,
    external: 0.16
  };

  // Animated lengths
  const lenArrival = values.arrival * circumference * ratio;
  const lenSeasonality = values.seasonality * circumference * ratio;
  const lenExternal = values.external * circumference * ratio;

  // Offsets
  // To rotate the chart such that it starts at 12 o'clock, we will rotate the svg container.
  // Offset represents how much to push the stroke forward
  const offsetArrival = 0;
  const offsetSeasonality = -lenArrival;
  const offsetExternal = -(lenArrival + lenSeasonality);

  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      {/* SVG Donut */}
      <div className="relative w-36 h-36">
        <svg 
          className="w-full h-full transform -rotate-90 filter drop-shadow-[0_0_12px_rgba(56,189,248,0.1)]" 
          viewBox="0 0 120 120"
        >
          {/* Base empty track */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#1e293b"
            strokeWidth={strokeWidth - 2}
          />

          {/* Arrival Segment (46%) */}
          {lenArrival > 0 && (
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke="#f59e0b" // amber-500
              strokeWidth={strokeWidth}
              strokeDasharray={`${lenArrival} ${circumference}`}
              strokeDashoffset={offsetArrival}
              strokeLinecap="round"
              className="transition-all duration-300 ease-out"
            />
          )}

          {/* Seasonality Segment (38%) */}
          {lenSeasonality > 0 && (
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke="#10b981" // emerald-500
              strokeWidth={strokeWidth}
              strokeDasharray={`${lenSeasonality} ${circumference}`}
              strokeDashoffset={offsetSeasonality}
              strokeLinecap="round"
              className="transition-all duration-300 ease-out"
            />
          )}

          {/* External Segment (16%) */}
          {lenExternal > 0 && (
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke="#8b5cf6" // violet-500
              strokeWidth={strokeWidth}
              strokeDasharray={`${lenExternal} ${circumference}`}
              strokeDashoffset={offsetExternal}
              strokeLinecap="round"
              className="transition-all duration-300 ease-out"
            />
          )}
        </svg>

        {/* Central Label inside the hole */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center font-mono">
          <motion.span 
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: ratio > 0.1 ? 1 : 0, scale: ratio > 0.1 ? 1 : 0.8 }}
            className="text-[10px] text-slate-500 font-bold tracking-wider"
          >
            DECISION
          </motion.span>
          <motion.span 
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: ratio > 0.1 ? 1 : 0, scale: ratio > 0.1 ? 1 : 0.8 }}
            className="text-lg font-extrabold text-sky-400 leading-none mt-0.5"
          >
            DNA
          </motion.span>
        </div>
      </div>

      {/* Mini Legend */}
      <div className="flex items-center gap-4 text-[9px] font-mono font-bold">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-slate-300">Arrival (46%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-slate-300">Seasonality (38%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-violet-500" />
          <span className="text-slate-300">External (16%)</span>
        </div>
      </div>
    </div>
  );
}
