import React from 'react';

interface AnimatedCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  glowColor?: 'accent' | 'bullish' | 'bearish' | 'neutral' | 'recovery';
  delayMs?: number;
}

export default function AnimatedCard({
  children,
  className = '',
  glowColor = 'accent',
  delayMs = 0,
  ...props
}: AnimatedCardProps) {
  // Map glow classes to colors defined in globals.css variables
  const glowClasses = {
    accent: 'border-sky-500/20 hover:border-sky-500/40 shadow-[0_0_20px_rgba(56,189,248,0.08)] hover:shadow-[0_0_25px_rgba(56,189,248,0.15)]',
    bullish: 'border-emerald-500/20 hover:border-emerald-500/40 shadow-[0_0_20px_rgba(52,211,153,0.08)] hover:shadow-[0_0_25px_rgba(52,211,153,0.15)]',
    bearish: 'border-rose-500/20 hover:border-rose-500/40 shadow-[0_0_20px_rgba(251,113,133,0.08)] hover:shadow-[0_0_25px_rgba(251,113,133,0.15)]',
    neutral: 'border-slate-500/20 hover:border-slate-500/40 shadow-[0_0_20px_rgba(148,163,184,0.08)] hover:shadow-[0_0_25px_rgba(148,163,184,0.15)]',
    recovery: 'border-violet-500/20 hover:border-violet-500/40 shadow-[0_0_20px_rgba(167,139,250,0.08)] hover:shadow-[0_0_25px_rgba(167,139,250,0.15)]',
  };

  return (
    <div
      style={{ animationDelay: `${delayMs}ms` }}
      className={`
        relative overflow-hidden rounded-xl border bg-slate-950/85 backdrop-blur-xl p-6
        transition-all duration-300 ease-out transform hover:-translate-y-0.5
        animate-[fadeInUp_400ms_ease-out_both]
        ${glowClasses[glowColor]}
        ${className}
      `}
      {...props}
    >
      {/* Dynamic diagonal highlight line to feel like a high-tech UI */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-sky-400/20 to-transparent" />
      <div className="absolute bottom-0 right-0 w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-400/10 to-transparent" />
      
      {/* Card Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
