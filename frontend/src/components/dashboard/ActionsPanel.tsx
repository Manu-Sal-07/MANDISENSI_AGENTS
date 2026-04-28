"use client";

import { motion } from "framer-motion";
import { Bell, Bookmark, Share2, Rocket } from "lucide-react";
import { useState } from "react";

export function ActionsPanel() {
  const [active, setActive] = useState<string | null>(null);

  const ActionButton = ({ icon: Icon, label, color, id }: { icon: any, label: string, color: string, id: string }) => (
    <motion.button
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={() => {
        setActive(id);
        setTimeout(() => setActive(null), 2000);
      }}
      className={`relative w-full flex items-center justify-center gap-3 p-4 rounded-2xl border bg-slate-950/60 transition-all duration-300 group overflow-hidden ${
        active === id ? `border-${color}-500 shadow-[0_0_20px_rgba(var(--${color}-rgb),0.3)]` : "border-white/5 hover:border-white/20"
      }`}
    >
      <div className={`absolute inset-0 bg-gradient-to-r from-${color}-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity`} />
      <Icon className={`w-5 h-5 ${active === id ? `text-${color}-500` : "text-slate-400 group-hover:text-white"}`} />
      <span className={`text-sm font-bold uppercase tracking-widest ${active === id ? `text-${color}-500` : "text-slate-400 group-hover:text-white"}`}>
        {active === id ? "Confirmed" : label}
      </span>
    </motion.button>
  );

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-slate-900/40 border border-white/10 rounded-3xl p-6 mt-6 backdrop-blur-md"
    >
      <div className="flex items-center gap-2 mb-6">
        <Rocket className="w-5 h-5 text-emerald-400" />
        <h2 className="text-lg font-bold text-white uppercase tracking-wider">Quick Actions</h2>
      </div>

      <div className="flex flex-col gap-4">
        <ActionButton icon={Bell} label="Set Price Alert" color="amber" id="alert" />
        <ActionButton icon={Bookmark} label="Add to Watchlist" color="emerald" id="watchlist" />
        <ActionButton icon={Share2} label="Share Insight" color="blue" id="share" />
      </div>
    </motion.div>
  );
}
