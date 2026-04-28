"use client";

import { useState } from "react";
import { Bell, Bookmark, Share2, Check } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useActionSystem } from "@/context/ActionContext";

export function QuickActions({ commodity = "tomato", mandi = "kolar" }: { commodity?: string, mandi?: string }) {
  const { watchlist, addToWatchlist, removeFromWatchlist, addAlert } = useActionSystem();
  
  const isWatched = watchlist.includes(commodity);
  const [showToast, setShowToast] = useState("");

  const handleWatchlist = () => {
    if (isWatched) {
      removeFromWatchlist(commodity);
      setShowToast("Removed from Watchlist");
    } else {
      addToWatchlist(commodity);
      setShowToast("Added to Watchlist");
    }
    setTimeout(() => setShowToast(""), 2000);
  };

  const handleAlert = () => {
    addAlert({ commodity, mandi, alert_type: "PRICE_DROP" });
    setShowToast("Price Drop Alert Set!");
    setTimeout(() => setShowToast(""), 2000);
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`MandiSense AI says SELL ${commodity} in ${mandi} now!`);
    setShowToast("Copied to clipboard!");
    setTimeout(() => setShowToast(""), 2000);
  };

  const ActionBtn = ({ icon, label, colorClass, onClick }: { icon: any, label: string, colorClass: string, onClick: () => void }) => (
    <motion.button 
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`flex flex-col items-center justify-center gap-2 p-3 rounded-2xl border bg-slate-900/50 backdrop-blur-sm ${colorClass} transition-all relative overflow-hidden`}
    >
      {icon}
      <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
    </motion.button>
  );

  return (
    <div className="relative">
      <div className="grid grid-cols-3 gap-3">
        <ActionBtn 
          icon={<Bell className="w-5 h-5 text-amber-500" />} 
          label="Set Alert" 
          colorClass="border-amber-500/20 hover:bg-amber-500/10 hover:border-amber-500/50" 
          onClick={handleAlert}
        />
        <ActionBtn 
          icon={isWatched ? <Check className="w-5 h-5 text-emerald-500" /> : <Bookmark className="w-5 h-5 text-emerald-500" />} 
          label={isWatched ? "Watching" : "Watchlist"} 
          colorClass={isWatched ? "bg-emerald-500/10 border-emerald-500/50" : "border-emerald-500/20 hover:bg-emerald-500/10 hover:border-emerald-500/50"} 
          onClick={handleWatchlist}
        />
        <ActionBtn 
          icon={<Share2 className="w-5 h-5 text-sky-500" />} 
          label="Share" 
          colorClass="border-sky-500/20 hover:bg-sky-500/10 hover:border-sky-500/50" 
          onClick={handleShare}
        />
      </div>

      <AnimatePresence>
        {showToast && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0, y: 10 }}
            className="absolute -top-12 left-0 right-0 mx-auto w-fit bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg z-50"
          >
            {showToast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
