'use client';

import React from 'react';
import { Cpu, Zap, Compass, AlertCircle } from 'lucide-react';

interface EvaluatorSectionProps {
  title: string;
  subtitle: string;
  purpose: string;
  accentColor?: 'cyan' | 'emerald' | 'violet' | 'amber';
  children: React.ReactNode;
}

export default function EvaluatorSection({
  title,
  subtitle,
  purpose,
  accentColor = 'cyan',
  children,
}: EvaluatorSectionProps) {
  // Map colors to design system tokens and Tailwind classes
  const colorMap = {
    cyan: {
      border: 'border-t-cyan-500/30 border-l-cyan-500/10',
      text: 'text-cyan-400',
      bgGlow: 'bg-cyan-500/5',
      badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      icon: <Zap className="w-5 h-5 text-cyan-400" />,
    },
    emerald: {
      border: 'border-t-emerald-500/30 border-l-emerald-500/10',
      text: 'text-emerald-400',
      bgGlow: 'bg-emerald-500/5',
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      icon: <Cpu className="w-5 h-5 text-emerald-400" />,
    },
    violet: {
      border: 'border-t-violet-500/30 border-l-violet-500/10',
      text: 'text-violet-400',
      bgGlow: 'bg-violet-500/5',
      badge: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
      icon: <Compass className="w-5 h-5 text-violet-400" />,
    },
    amber: {
      border: 'border-t-amber-500/30 border-l-amber-500/10',
      text: 'text-amber-400',
      bgGlow: 'bg-amber-500/5',
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      icon: <AlertCircle className="w-5 h-5 text-amber-400" />,
    },
  };

  const currentTheme = colorMap[accentColor];

  return (
    <section 
      className={`
        relative w-full rounded-[2rem] p-6 md:p-8
        bg-[#09101d]/90 backdrop-blur-xl border border-slate-900/80
        shadow-[0_20px_50px_rgba(0,0,0,0.5),_inset_0_1px_1px_rgba(255,255,255,0.03)]
        ${currentTheme.border} transition-all duration-300 overflow-hidden
      `}
    >
      {/* Background ambient glow */}
      <div className={`absolute -top-20 -left-20 w-64 h-64 rounded-full blur-[100px] pointer-events-none opacity-40 ${currentTheme.bgGlow}`} />
      
      {/* Tech grid texture overlay */}
      <div className="absolute inset-0 opacity-[0.015] pointer-events-none bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:16px_16px]" />

      {/* Header telemetry area */}
      <div className="relative z-10 flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-8 border-b border-slate-900 pb-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1.5 text-[10px] font-bold tracking-[0.2em] px-2.5 py-0.5 rounded-full border uppercase font-mono ${currentTheme.badge}`}>
              {currentTheme.icon}
              {title}
            </span>
          </div>
          <h2 className="text-xl md:text-2xl font-black text-slate-100 tracking-tight">
            {subtitle}
          </h2>
        </div>

        {/* Section Purpose description */}
        <div className="md:max-w-md bg-slate-950/40 border border-slate-900 px-4 py-3 rounded-xl">
          <span className="block text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            Section Purpose / Context
          </span>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            {purpose}
          </p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="relative z-10 w-full">
        {children}
      </div>
    </section>
  );
}
