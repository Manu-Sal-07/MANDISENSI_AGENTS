'use client';

import React from 'react';
import { Database, Cpu, BrainCircuit, Activity, Network, CheckCircle } from 'lucide-react';

interface SubItem {
  label: string;
  details?: string;
  badge?: string;
}

interface EvaluatorFlowNodeProps {
  label: string;
  description?: string;
  subItems?: (string | SubItem)[];
  children?: React.ReactNode;
  status?: 'default' | 'active' | 'completed' | 'warning';
  accentColor?: 'cyan' | 'emerald' | 'violet' | 'amber';
  journeyStatus?: 'idle' | 'active' | 'completed' | 'dimmed';
  onSelect?: () => void;
}

export default function EvaluatorFlowNode({
  label,
  description,
  subItems,
  children,
  status = 'default',
  accentColor = 'cyan',
  journeyStatus = 'idle',
  onSelect,
}: EvaluatorFlowNodeProps) {
  // Theme styling based on accent color (default state style)
  const colorMap = {
    cyan: {
      border: 'border-cyan-500/20 hover:border-cyan-400/45',
      text: 'text-cyan-400',
      glow: 'shadow-[0_0_15px_rgba(6,182,212,0.1)]',
      dot: 'bg-cyan-500',
      badge: 'bg-cyan-950/40 text-cyan-400 border-cyan-500/20',
      subText: 'text-cyan-300',
    },
    emerald: {
      border: 'border-emerald-500/20 hover:border-emerald-400/45',
      text: 'text-emerald-400',
      glow: 'shadow-[0_0_15px_rgba(16,185,129,0.1)]',
      dot: 'bg-emerald-500',
      badge: 'bg-emerald-950/40 text-emerald-400 border-emerald-500/20',
      subText: 'text-emerald-300',
    },
    violet: {
      border: 'border-violet-500/20 hover:border-violet-400/45',
      text: 'text-violet-400',
      glow: 'shadow-[0_0_15px_rgba(139,92,246,0.1)]',
      dot: 'bg-violet-500',
      badge: 'bg-violet-950/40 text-violet-400 border-violet-500/20',
      subText: 'text-violet-300',
    },
    amber: {
      border: 'border-amber-500/20 hover:border-amber-400/45',
      text: 'text-amber-400',
      glow: 'shadow-[0_0_15px_rgba(245,158,11,0.1)]',
      dot: 'bg-amber-500',
      badge: 'bg-amber-950/40 text-amber-400 border-amber-500/20',
      subText: 'text-amber-300',
    },
  };

  const theme = colorMap[accentColor];

  // Helper to determine node icon
  const getIcon = () => {
    const lowerLabel = label.toLowerCase();
    if (lowerLabel.includes('data') || lowerLabel.includes('registry')) {
      return <Database className="w-4.5 h-4.5" />;
    }
    if (lowerLabel.includes('model') && !lowerLabel.includes('agent')) {
      return <Cpu className="w-4.5 h-4.5" />;
    }
    if (lowerLabel.includes('agent') || lowerLabel.includes('intelligence')) {
      return <BrainCircuit className="w-4.5 h-4.5" />;
    }
    if (lowerLabel.includes('ensemble') || lowerLabel.includes('reasoning')) {
      return <Network className="w-4.5 h-4.5" />;
    }
    return <Activity className="w-4.5 h-4.5" />;
  };

  // Determine styles dynamically based on journeyStatus
  let cardStyles = `bg-slate-950/70 border backdrop-blur-md ${theme.border} ${theme.glow}`;
  let statusText = status.toUpperCase();
  let statusIndicator = <span className={`w-2 h-2 rounded-full ${theme.dot}`} />;

  if (journeyStatus === 'active') {
    cardStyles = 'bg-slate-900/90 border-emerald-500 scale-[1.02] shadow-[0_0_25px_rgba(16,185,129,0.3)] duration-300 animate-[activePulse_2s_infinite_ease-in-out]';
    statusText = 'RUNNING';
    statusIndicator = (
      <div className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </div>
    );
  } else if (journeyStatus === 'completed') {
    cardStyles = 'bg-slate-950/50 border-slate-800 opacity-80';
    statusText = 'COMPLETED';
    statusIndicator = <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
  } else if (journeyStatus === 'dimmed') {
    cardStyles = 'bg-slate-950/10 border-slate-900/40 opacity-20 pointer-events-none scale-[0.98] shadow-none';
    statusText = 'PENDING';
    statusIndicator = <span className="w-2 h-2 rounded-full bg-slate-800" />;
  }

  // Interactive styling if clickable
  const clickableClasses = onSelect
    ? 'cursor-pointer hover:border-indigo-500/60 hover:shadow-[0_0_20px_rgba(99,102,241,0.15)] group/node'
    : 'group';

  return (
    <div 
      onClick={onSelect}
      className={`
        flex-1 min-w-[280px] max-w-sm rounded-2xl p-5
        transition-all duration-500 relative overflow-hidden
        ${cardStyles} ${clickableClasses}
      `}
    >
      {/* Inline styles for pulse animations */}
      {journeyStatus === 'active' && (
        <style dangerouslySetInnerHTML={{__html: `
          @keyframes activePulse {
            0%, 100% { border-color: rgba(16, 185, 129, 0.4); box-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }
            50% { border-color: rgba(52, 211, 153, 0.85); box-shadow: 0 0 25px rgba(16, 185, 129, 0.5); }
          }
        `}} />
      )}

      {/* Node Header */}
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className={`
            p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400
            ${journeyStatus === 'active' ? 'text-emerald-400 border-emerald-500/20' : ''}
            ${journeyStatus === 'completed' ? 'text-emerald-500/60 border-slate-800' : ''}
            group-hover/node:text-indigo-400 group-hover/node:border-indigo-500/20
            transition-colors duration-300
          `}>
            {getIcon()}
          </div>
          <div>
            <h4 className={`
              text-sm font-black tracking-tight transition-colors
              ${journeyStatus === 'dimmed' ? 'text-slate-650' : 'text-slate-100'}
              ${journeyStatus === 'active' ? 'text-white' : ''}
              group-hover/node:text-white
            `}>
              {label}
            </h4>
            {description && (
              <span className={`
                text-[9px] font-mono block tracking-wide
                ${journeyStatus === 'dimmed' ? 'text-slate-750' : 'text-slate-550'}
              `}>
                {description}
              </span>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-1.5">
          {statusIndicator}
          <span className={`
            text-[9px] font-mono font-bold tracking-wider uppercase
            ${journeyStatus === 'active' ? 'text-emerald-400' : ''}
            ${journeyStatus === 'completed' ? 'text-emerald-500' : ''}
            ${journeyStatus === 'dimmed' ? 'text-slate-750' : 'text-slate-400'}
          `}>
            {statusText}
          </span>
        </div>
      </div>

      {/* Custom children override subItems when provided */}
      {children && (
        <div className={`mt-3.5 pt-3 border-t transition-opacity duration-300 ${journeyStatus === 'dimmed' ? 'border-slate-900/20 opacity-30' : 'border-slate-900/60'}`}>
          {children}
        </div>
      )}

      {/* Sub-items content block (only if no children) */}
      {!children && subItems && subItems.length > 0 && (
        <div className={`
          mt-3.5 pt-3 border-t space-y-2.5 transition-opacity duration-300
          ${journeyStatus === 'dimmed' ? 'border-slate-900/20' : 'border-slate-900/60'}
        `}>
          <div className={`
            text-[9px] font-mono uppercase tracking-widest
            ${journeyStatus === 'dimmed' ? 'text-slate-700' : 'text-slate-550'}
          `}>
            Telemetry / Attributes
          </div>
          <div className="space-y-2">
            {subItems.map((item, idx) => {
              const isString = typeof item === 'string';
              const itemLabel = isString ? item : item.label;
              const itemDetails = isString ? undefined : item.details;
              const itemBadge = isString ? undefined : item.badge;

              return (
                <div 
                  key={idx} 
                  className={`
                    flex items-center justify-between text-xs border rounded-xl px-3.5 py-2 transition-colors
                    ${journeyStatus === 'dimmed' 
                      ? 'bg-slate-950/5 border-slate-950/20 text-slate-700' 
                      : 'bg-slate-950/80 border-slate-900/40 text-slate-300 hover:border-slate-800'
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <div className={`
                      w-1 h-1 rounded-full opacity-60
                      ${journeyStatus === 'dimmed' ? 'bg-slate-850' : theme.dot}
                    `} />
                    <div>
                      <span className={`
                        font-bold text-xs tracking-tight
                        ${journeyStatus === 'dimmed' ? 'text-slate-650' : 'text-slate-200'}
                      `}>
                        {itemLabel}
                      </span>
                      {itemDetails && (
                        <span className={`
                          block text-[8px] font-mono mt-0.5 leading-none
                          ${journeyStatus === 'dimmed' ? 'text-slate-750' : 'text-slate-550'}
                        `}>
                          {itemDetails}
                        </span>
                      )}
                    </div>
                  </div>

                  {itemBadge && (
                    <span className={`
                      text-[9px] font-mono font-bold tracking-wider px-2 py-0.5 rounded border
                      ${journeyStatus === 'dimmed' 
                        ? 'bg-slate-950/10 text-slate-700 border-slate-900/20' 
                        : theme.badge
                      }
                    `}>
                      {itemBadge}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
