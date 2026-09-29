import React from 'react';
import { motion, Variants } from 'framer-motion';
import { Award, ArrowUpRight } from 'lucide-react';

interface Influencer {
  rank: number;
  label: string;
  impact: string;
  badgeColor: string;
}

interface InfluenceRankingProps {
  details?: { label: string; impact: string }[];
}

export default function InfluenceRanking({ details }: InfluenceRankingProps) {
  // Map provided details to influencers list, falling back to defaults if not present
  const defaultDetails = [
    { label: "Supply Stress", impact: "+24%" },
    { label: "Festival Demand", impact: "+18%" },
    { label: "Weather Outlook", impact: "+7%" }
  ];

  const sourceDetails = details && details.length >= 3 ? details.slice(0, 3) : defaultDetails;
  
  const colors = [
    "text-amber-400 bg-amber-500/10 border-amber-500/30",
    "text-sky-300 bg-sky-500/10 border-sky-500/30",
    "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
  ];

  const influencers: Influencer[] = sourceDetails.map((item, idx) => ({
    rank: idx + 1,
    label: item.label.replace(" Impact", ""),
    impact: item.impact,
    badgeColor: colors[idx % colors.length]
  }));

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15
      }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, x: -15 },
    show: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 100 } }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-widest font-mono">
        <Award className="w-4 h-4 text-sky-450" />
        <span>Top Decision Influencers</span>
      </div>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="space-y-2"
      >
        {influencers.map((inf) => (
          <motion.div 
            key={inf.rank}
            variants={itemVariants}
            className={`
              flex items-center justify-between p-3 rounded-lg border border-slate-900 bg-slate-950/60
              font-mono transition-colors duration-300 hover:bg-slate-900/40 hover:border-slate-800
            `}
          >
            <div className="flex items-center gap-3">
              <span className={`text-[10px] font-extrabold border px-2.5 py-0.5 rounded-md ${inf.badgeColor}`}>
                #{inf.rank}
              </span>
              <span className="text-xs font-bold text-slate-200">{inf.label}</span>
            </div>
            
            <div className="flex items-center gap-1">
              <span className="text-xs font-extrabold text-emerald-400">{inf.impact}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500" />
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
