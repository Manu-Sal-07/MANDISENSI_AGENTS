import React from 'react';
import NodeStatusIndicator, { NodeState } from './NodeStatusIndicator';

interface WorkflowNodeProps {
  label: string;
  actionText: string;
  state: NodeState;
}

export default function WorkflowNode({
  label,
  actionText,
  state,
}: WorkflowNodeProps) {
  return (
    <div 
      className={`
        flex items-center gap-4 py-1.5 px-3 rounded-lg transition-all duration-300
        ${state === 'running' ? 'bg-sky-500/5 border border-sky-500/10' : 'border border-transparent'}
      `}
    >
      {/* Node status circle indicator */}
      <NodeStatusIndicator state={state} />

      {/* Node text content */}
      <div className="flex-1 min-w-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-1.5">
          <span 
            className={`text-sm font-semibold tracking-wide transition-colors duration-300 ${
              state === 'completed' 
                ? 'text-emerald-400' 
                : state === 'running' 
                  ? 'text-sky-300' 
                  : 'text-slate-500'
            }`}
          >
            {label}
          </span>
          
          {/* Active running details text */}
          {state === 'running' && (
            <span className="text-[10px] font-mono text-sky-400/80 animate-pulse bg-sky-950/20 px-2 py-0.5 rounded border border-sky-500/10 self-start md:self-auto">
              {actionText}
            </span>
          )}

          {/* Completed state tag (optional clean look) */}
          {state === 'completed' && (
            <span className="text-[10px] font-mono text-emerald-500/80 bg-emerald-950/10 px-2 py-0.5 rounded border border-emerald-500/10 self-start md:self-auto uppercase font-bold tracking-wider">
              Completed
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
