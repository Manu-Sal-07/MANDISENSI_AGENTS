import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Layers, TrendingUp, BarChart3, Radio } from 'lucide-react';

interface MetaFusionNodeProps {
  progress: number; // 0 to 100
}

export default function MetaFusionNode({ progress }: MetaFusionNodeProps) {
  // progress phases:
  // 0 - 15%: Receiving Agent Outputs (glide cards toward center)
  // 15% - 45%: Fusion Chamber Animation (particle flow, core glowing)
  // >= 45%: Fused / Complete
  
  const isReceiving = progress < 15;
  const isFusing = progress >= 15 && progress < 45;
  const isCompleted = progress >= 45;

  // Calculate interpolation values for the cards (gliding to center)
  // Card 1: Seasonality (Top Left)
  // Card 2: Arrival (Top Right)
  // Card 3: External (Bottom Center)
  
  // Handlers for card positions based on progress
  const getCardOffset = (index: number) => {
    if (progress >= 15) return { x: 0, y: 0, scale: 0.85, opacity: 0.3 };
    
    // Scale progress between 0 and 15
    const ratio = progress / 15;
    
    if (index === 0) {
      // Top-Left to center
      return { x: -80 * (1 - ratio), y: -50 * (1 - ratio), scale: 1 - 0.15 * ratio, opacity: 1 };
    } else if (index === 1) {
      // Top-Right to center
      return { x: 80 * (1 - ratio), y: -50 * (1 - ratio), scale: 1 - 0.15 * ratio, opacity: 1 };
    } else {
      // Bottom to center
      return { x: 0, y: 60 * (1 - ratio), scale: 1 - 0.15 * ratio, opacity: 1 };
    }
  };

  const agents = [
    {
      name: "Seasonality",
      icon: <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />,
      title: "Seasonality Agent",
      pred: "+4.2%",
      conf: "82%",
      color: "border-emerald-500/30 bg-emerald-950/20"
    },
    {
      name: "Arrival",
      icon: <BarChart3 className="w-3.5 h-3.5 text-amber-400" />,
      title: "Arrival Volume Agent",
      pred: "+6.8%",
      conf: "89%",
      color: "border-amber-500/30 bg-amber-950/20"
    },
    {
      name: "External",
      icon: <Radio className="w-3.5 h-3.5 text-violet-400" />,
      title: "External Agent",
      pred: "+1.1%",
      conf: "74%",
      color: "border-violet-500/30 bg-violet-950/20"
    }
  ];

  return (
    <div className="relative w-full h-[280px] bg-slate-950/40 rounded-xl border border-slate-900 overflow-hidden flex items-center justify-center">
      {/* Grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:20px_20px] opacity-20" />
      
      {/* SVG Connecting Tracks */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        {/* Seasonality track */}
        <line x1="28%" y1="28%" x2="50%" y2="50%" stroke="rgba(148, 163, 184, 0.15)" strokeWidth="1.5" strokeDasharray="4 4" />
        {/* Arrival track */}
        <line x1="72%" y1="28%" x2="50%" y2="50%" stroke="rgba(148, 163, 184, 0.15)" strokeWidth="1.5" strokeDasharray="4 4" />
        {/* External track */}
        <line x1="50%" y1="78%" x2="50%" y2="50%" stroke="rgba(148, 163, 184, 0.15)" strokeWidth="1.5" strokeDasharray="4 4" />

        {/* Moving flow particles when Fusing */}
        {isFusing && (
          <>
            {/* Seasonality Particle */}
            <circle r="4" fill="#34d399" className="shadow-[0_0_8px_#34d399]">
              <animateMotion dur="1.2s" repeatCount="indefinite" path="M 120 78 L 225 140" />
            </circle>
            {/* Arrival Particle */}
            <circle r="4" fill="#fbbf24" className="shadow-[0_0_8px_#fbbf24]">
              <animateMotion dur="1.2s" repeatCount="indefinite" path="M 330 78 L 225 140" />
            </circle>
            {/* External Particle */}
            <circle r="4" fill="#a78bfa" className="shadow-[0_0_8px_#a78bfa]">
              <animateMotion dur="1.2s" repeatCount="indefinite" path="M 225 218 L 225 140" />
            </circle>
          </>
        )}
      </svg>

      {/* Central Fusion Chamber Node: META ENSEMBLE */}
      <div className="absolute z-20 flex flex-col items-center">
        <motion.div 
          animate={{
            scale: isFusing ? [1, 1.12, 1] : 1,
            boxShadow: isFusing 
              ? [
                  "0 0 20px rgba(56, 189, 248, 0.2)", 
                  "0 0 40px rgba(56, 189, 248, 0.5)", 
                  "0 0 20px rgba(56, 189, 248, 0.2)"
                ] 
              : "0 0 15px rgba(56, 189, 248, 0.15)"
          }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          className={`
            w-16 h-16 rounded-full border flex items-center justify-center
            ${isCompleted 
              ? 'border-emerald-500 bg-emerald-950/50 text-emerald-400' 
              : isFusing 
                ? 'border-sky-400 bg-sky-950/40 text-sky-400' 
                : 'border-slate-800 bg-slate-900 text-slate-400'}
          `}
        >
          <Layers className={`w-7 h-7 ${isFusing ? 'animate-[spin_4s_linear_infinite]' : ''}`} />
        </motion.div>
        
        <div className="text-center mt-3 font-mono">
          <span className={`text-[10px] font-bold block tracking-wider ${isCompleted ? 'text-emerald-400' : isFusing ? 'text-sky-300' : 'text-slate-400'}`}>
            {isCompleted ? 'META ENSEMBLE FUSED' : isFusing ? 'FUSION ACTIVE' : 'AWAITING AGENTS'}
          </span>
          <span className="text-[8px] text-slate-500 block uppercase">AI DECISION CORE</span>
        </div>
      </div>

      {/* Spaced Outer Cards */}
      <AnimatePresence>
        {(!isCompleted) && (
          <div className="absolute inset-0 z-10 w-full h-full pointer-events-none">
            {/* Card 1: Seasonality */}
            <motion.div 
              style={{ pointerEvents: 'auto' }}
              animate={getCardOffset(0)}
              transition={{ type: 'spring', stiffness: 80, damping: 12 }}
              className={`absolute top-[18%] left-[8%] md:left-[16%] w-[130px] border rounded-lg p-2 font-mono text-[9px] ${agents[0].color} shadow-lg`}
            >
              <div className="flex items-center gap-1.5 border-b border-slate-800 pb-1 mb-1">
                {agents[0].icon}
                <span className="text-slate-200 font-bold">Seasonality</span>
              </div>
              <div className="text-slate-400 space-y-0.5">
                <div className="flex justify-between">
                  <span>Pred:</span>
                  <span className="text-emerald-400">{agents[0].pred}</span>
                </div>
                <div className="flex justify-between">
                  <span>Conf:</span>
                  <span className="text-slate-300">{agents[0].conf}</span>
                </div>
              </div>
            </motion.div>

            {/* Card 2: Arrival */}
            <motion.div 
              style={{ pointerEvents: 'auto' }}
              animate={getCardOffset(1)}
              transition={{ type: 'spring', stiffness: 80, damping: 12 }}
              className={`absolute top-[18%] right-[8%] md:right-[16%] w-[130px] border rounded-lg p-2 font-mono text-[9px] ${agents[1].color} shadow-lg`}
            >
              <div className="flex items-center gap-1.5 border-b border-slate-800 pb-1 mb-1">
                {agents[1].icon}
                <span className="text-slate-200 font-bold">Arrival</span>
              </div>
              <div className="text-slate-400 space-y-0.5">
                <div className="flex justify-between">
                  <span>Pred:</span>
                  <span className="text-emerald-400">{agents[1].pred}</span>
                </div>
                <div className="flex justify-between">
                  <span>Conf:</span>
                  <span className="text-slate-300">{agents[1].conf}</span>
                </div>
              </div>
            </motion.div>

            {/* Card 3: External */}
            <motion.div 
              style={{ pointerEvents: 'auto' }}
              animate={getCardOffset(2)}
              transition={{ type: 'spring', stiffness: 80, damping: 12 }}
              className={`absolute bottom-[8%] left-1/2 -translate-x-1/2 w-[130px] border rounded-lg p-2 font-mono text-[9px] ${agents[2].color} shadow-lg`}
            >
              <div className="flex items-center gap-1.5 border-b border-slate-800 pb-1 mb-1">
                {agents[2].icon}
                <span className="text-slate-200 font-bold">External</span>
              </div>
              <div className="text-slate-400 space-y-0.5">
                <div className="flex justify-between">
                  <span>Impact:</span>
                  <span className="text-sky-400">{agents[2].pred}</span>
                </div>
                <div className="flex justify-between">
                  <span>Conf:</span>
                  <span className="text-slate-300">{agents[2].conf}</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
