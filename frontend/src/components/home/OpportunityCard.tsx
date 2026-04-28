"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export interface OpportunityData {
  id: string;
  name: string;
  signal: "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "AVOID";
  score: number; // 0-10
  change: number; // Percentage
  confidence: number; // 0-1
}

interface OpportunityCardProps {
  data: OpportunityData;
  index: number;
}

export function OpportunityCard({ data, index }: OpportunityCardProps) {
  // Determine color coding based on signal
  const isBullish = ["STRONG BUY", "BUY"].includes(data.signal);
  const isBearish = ["SELL", "AVOID"].includes(data.signal);
  const isNeutral = data.signal === "HOLD";

  let colorClass = "text-yellow-500";
  let bgGlow = "hover:shadow-yellow-500/20";
  let borderGlow = "group-hover:border-yellow-500/50";
  let Icon = Minus;

  if (isBullish) {
    colorClass = "text-emerald-500";
    bgGlow = "hover:shadow-emerald-500/20";
    borderGlow = "group-hover:border-emerald-500/50";
    Icon = TrendingUp;
  } else if (isBearish) {
    colorClass = "text-rose-500";
    bgGlow = "hover:shadow-rose-500/20";
    borderGlow = "group-hover:border-rose-500/50";
    Icon = TrendingDown;
  }

  return (
    <Link href={`/commodity/${data.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: index * 0.1 }}
        whileHover={{ scale: 1.02 }}
        className="block group h-full"
      >
        <Card className={`h-full bg-card/60 backdrop-blur-md border-border/50 transition-all duration-300 overflow-hidden ${bgGlow} ${borderGlow}`}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <h3 className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
              {data.name}
            </h3>
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-background/50 border border-border text-xs font-bold tracking-wider ${colorClass}`}>
              <Icon className="w-3.5 h-3.5" />
              {data.signal}
            </div>
          </CardHeader>
          
          <CardContent>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-5xl font-black tracking-tighter text-foreground">
                {data.score.toFixed(1)}
              </span>
              <span className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
                Score
              </span>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Predicted 7D
                </span>
                <span className={`text-lg font-semibold flex items-center gap-1 ${colorClass}`}>
                  {data.change > 0 ? "+" : ""}{data.change.toFixed(1)}%
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Confidence
                </span>
                <span className="text-lg font-semibold text-foreground flex items-center gap-1">
                  <Activity className="w-4 h-4 text-muted-foreground" />
                  {(data.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </Link>
  );
}
