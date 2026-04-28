"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  glowColor?: "green" | "orange" | "red" | "blue";
  delay?: number;
}

export function MetricCard({ title, icon, children, className, glowColor = "blue", delay = 0 }: MetricCardProps) {
  const glowMaps = {
    green: "shadow-[0_0_25px_rgba(34,197,94,0.15)] border-emerald-500/20",
    orange: "shadow-[0_0_25px_rgba(245,158,11,0.15)] border-amber-500/20",
    red: "shadow-[0_0_25px_rgba(239,68,68,0.15)] border-rose-500/20",
    blue: "shadow-[0_0_25px_rgba(56,189,248,0.15)] border-sky-500/20",
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.02 }}
      className={cn(
        "relative flex flex-col p-5 rounded-2xl overflow-hidden transition-all duration-300",
        "bg-gradient-to-br from-slate-900/90 to-slate-950/90 backdrop-blur-xl border",
        glowMaps[glowColor],
        className
      )}
    >
      <div className="flex items-center gap-2 mb-3 z-10">
        {icon && <div className="text-muted-foreground">{icon}</div>}
        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider">{title}</h3>
      </div>
      <div className="z-10 flex-1 flex flex-col justify-center">
        {children}
      </div>
    </motion.div>
  );
}
