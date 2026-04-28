"use client";

import { motion } from "framer-motion";
import { Zap } from "lucide-react";

interface DriversPanelProps {
  supply: number;
  demand: number;
  weather: number;
  seasonality: number;
}

export function DriversPanel({ supply, demand, weather, seasonality }: DriversPanelProps) {
  const DriverBar = ({ label, value, color }: { label: string, value: number, color: string }) => (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-bold text-slate-300">{label}</span>
        <span className={`text-sm font-black ${color}`}>{value}%</span>
      </div>
      <div className="h-3 w-full bg-slate-950 rounded-full overflow-hidden border border-white/5">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${Math.abs(value)}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className={`h-full rounded-full ${color.replace('text-', 'bg-')}`} 
        />
      </div>
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-slate-900/40 border border-white/10 rounded-3xl p-6 mt-6 backdrop-blur-md"
    >
      <div className="flex items-center gap-2 mb-6">
        <Zap className="w-5 h-5 text-amber-400" />
        <h2 className="text-lg font-bold text-white uppercase tracking-wider">Key Impact Drivers</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
        <DriverBar label="Supply Volume" value={supply} color="text-rose-500" />
        <DriverBar label="Market Demand" value={demand} color="text-emerald-500" />
        <DriverBar label="Weather Impact" value={weather} color="text-blue-500" />
        <DriverBar label="Seasonal Trend" value={seasonality} color="text-purple-500" />
      </div>
    </motion.div>
  );
}
