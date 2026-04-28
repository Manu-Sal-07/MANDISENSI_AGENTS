"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, Users, ShoppingCart, BarChart3 } from "lucide-react";

interface MarketPanelProps {
  arrivals: "High" | "Low" | "Medium";
  demand: "Strong" | "Weak" | "Stable";
  trend: "Upward" | "Downward" | "Sideways";
}

export function MarketPanel({ arrivals, demand, trend }: MarketPanelProps) {
  const StatItem = ({ icon: Icon, label, value, color }: { icon: any, label: string, value: string, color: string }) => (
    <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-950/40 border border-white/5">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-slate-900 border border-white/5 ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <span className="text-sm font-bold text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <span className={`text-lg font-black ${color}`}>{value}</span>
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-slate-900/40 border border-white/10 rounded-3xl p-6 backdrop-blur-md"
    >
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 className="w-5 h-5 text-purple-400" />
        <h2 className="text-lg font-bold text-white uppercase tracking-wider">Market Dynamics</h2>
      </div>

      <div className="flex flex-col gap-4">
        <StatItem 
          icon={Users} 
          label="Arrivals" 
          value={arrivals} 
          color={arrivals === 'High' ? 'text-rose-500' : 'text-emerald-500'} 
        />
        <StatItem 
          icon={ShoppingCart} 
          label="Demand" 
          value={demand} 
          color={demand === 'Strong' ? 'text-emerald-500' : 'text-amber-500'} 
        />
        <StatItem 
          icon={trend === 'Upward' ? ArrowUpRight : ArrowDownRight} 
          label="Trend" 
          value={trend} 
          color={trend === 'Upward' ? 'text-emerald-500' : 'text-rose-500'} 
        />
      </div>
    </motion.div>
  );
}
