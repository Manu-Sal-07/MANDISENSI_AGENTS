import React from 'react';
import { Layers } from 'lucide-react';

interface FusionOrbitProps {
  progress: number; // 0 to 100
}

export default function FusionOrbit({ progress }: FusionOrbitProps) {
  // Orbit phase is active between progress 40 and 75
  const active = progress >= 40 && progress < 75;
  if (!active) return null;

  // Normalize progress between 40 and 75 to 0.0 -> 1.0
  const t = (progress - 40) / (75 - 40);

  // Orbit parameters
  const rotationAngle = t * Math.PI * 4; // 2 full rotations
  const baseRadius = 80; // base radius in pixels
  const currentRadius = baseRadius * (1 - t); // shrink to 0 as t approaches 1
  const opacity = 1 - Math.pow(t, 4); // fade out at the very end

  const signals = [
    { label: "Trend", angleOffset: 0, color: "text-emerald-400 border-emerald-500/30 bg-emerald-950/80 shadow-[0_0_8px_rgba(52,211,153,0.3)]" },
    { label: "Supply", angleOffset: Math.PI / 2, color: "text-amber-400 border-amber-500/30 bg-amber-950/80 shadow-[0_0_8px_rgba(245,158,11,0.3)]" },
    { label: "Weather", angleOffset: Math.PI, color: "text-violet-400 border-violet-500/30 bg-violet-950/80 shadow-[0_0_8px_rgba(139,92,246,0.3)]" },
    { label: "Festival", angleOffset: (3 * Math.PI) / 2, color: "text-rose-400 border-rose-500/30 bg-rose-950/80 shadow-[0_0_8px_rgba(244,63,94,0.3)]" }
  ];

  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
      <div className="relative w-48 h-48 flex items-center justify-center">
        
        {/* Orbital rings */}
        <div 
          className="absolute border border-sky-500/15 rounded-full border-dashed animate-[spin_12s_linear_infinite]"
          style={{ 
            width: `${currentRadius * 2}px`, 
            height: `${currentRadius * 2}px`,
            opacity: opacity 
          }} 
        />
        
        {/* Central Fusion Core */}
        <div className="relative w-14 h-14 rounded-full bg-sky-950/50 border-2 border-sky-400 flex items-center justify-center shadow-[0_0_25px_rgba(56,189,248,0.4)] animate-[pulse_1.5s_infinite]">
          <Layers className="w-6 h-6 text-sky-400 animate-[spin_8s_linear_infinite]" />
          
          {/* Inner collapse glow */}
          {t > 0.7 && (
            <div 
              className="absolute inset-0 rounded-full bg-sky-400/30 animate-ping"
              style={{ transform: `scale(${1 + (t - 0.7) * 3})` }}
            />
          )}
        </div>

        {/* Orbiting Signal packets */}
        {signals.map((sig, idx) => {
          const angle = rotationAngle + sig.angleOffset;
          const x = Math.cos(angle) * currentRadius;
          const y = Math.sin(angle) * currentRadius;

          return (
            <div
              key={idx}
              className={`
                absolute px-2 py-0.5 rounded border text-[8px] font-extrabold font-mono uppercase tracking-wider
                transition-all duration-75 flex items-center justify-center whitespace-nowrap
                ${sig.color}
              `}
              style={{
                transform: `translate(${x}px, ${y}px)`,
                opacity: opacity
              }}
            >
              {sig.label}
            </div>
          );
        })}

        {/* Status indicator text */}
        <div className="absolute bottom-[-28px] text-center font-mono text-[9px] uppercase tracking-widest text-sky-400 font-extrabold animate-pulse">
          Consensus Building...
        </div>

      </div>
    </div>
  );
}
