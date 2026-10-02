import React from 'react';
import { Compass, CheckCircle2 } from 'lucide-react';
import { AgentWorkflowConfig } from '../workflowConfig';
import WorkflowNode from './WorkflowNode';
import ConnectionLine from './ConnectionLine';

interface AgentWorkflowCardProps {
  config: AgentWorkflowConfig;
  progress: number; // 0 to 100
}

export default function AgentWorkflowCard({ config, progress }: AgentWorkflowCardProps) {
  const nodeCount = config.nodes.length;
  const stepSize = 100 / nodeCount; // 20% for 5 nodes

  // Determine node states
  const getNodeState = (index: number) => {
    const startProgress = index * stepSize;
    const endProgress = (index + 1) * stepSize;

    if (progress < startProgress) return 'idle';
    if (progress >= startProgress && progress < endProgress) return 'running';
    return 'completed';
  };

  const isSimulationCompleted = progress >= 99.5;

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Expanded Accordion Card */}
      <div 
        className={`
          border bg-slate-950/80 rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.3)]
          transition-all duration-500 ease-out border-slate-800
        `}
      >
        {/* Card Header */}
        <div className="bg-slate-900/90 px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-950 border border-slate-700 flex items-center justify-center">
              <Compass className="w-4.5 h-4.5 text-sky-400 animate-[spin_12s_linear_infinite]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">{config.agentName}</h3>
              <p className="text-[9px] text-slate-500 font-mono mt-0.5">COGNITIVE_PIPELINE_RESOLVING</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isSimulationCompleted ? (
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full uppercase tracking-wider font-mono">
                SUCCESS
              </span>
            ) : (
              <span className="text-[10px] font-bold text-sky-400 bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 rounded-full uppercase tracking-wider font-mono animate-pulse">
                THINKING
              </span>
            )}
          </div>
        </div>

        {/* Nodes and Connection Lines List */}
        <div className="p-5 space-y-0.5 bg-slate-950/40">
          {config.nodes.map((node, index) => {
            const nodeState = getNodeState(index);
            const isLastNode = index === nodeCount - 1;

            // Connection line is active when the current node is completed and the next node is running
            const isLineActive = progress >= (index + 1) * stepSize && progress < (index + 2) * stepSize;
            // Connection line is completed when the next node is completed
            const isLineCompleted = progress >= (index + 2) * stepSize;

            return (
              <div key={index} className="flex flex-col">
                <WorkflowNode
                  label={node.label}
                  actionText={node.actionText}
                  state={nodeState}
                />
                {!isLastNode && (
                  <ConnectionLine
                    active={isLineActive}
                    completed={isLineCompleted}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Accordion Footer Panel: Fades in only upon completed reasoning */}
        <div 
          className={`
            border-t border-slate-900 bg-slate-950/90 p-5 transition-all duration-500 ease-in-out
            ${isSimulationCompleted ? 'max-h-[300px] opacity-100 py-5' : 'max-h-0 opacity-0 py-0 overflow-hidden border-t-0'}
          `}
        >
          {isSimulationCompleted && (
            <div className="space-y-4 animate-[fadeInUp_400ms_ease-out_both]">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>RESOLVED AGENT TENSOR OUTPUTS</span>
              </div>
              
              <div className="grid grid-cols-3 gap-2">
                {config.outputs.map((out, i) => (
                  <div key={i} className="bg-slate-900 border border-slate-900 p-2.5 rounded-lg text-center font-mono">
                    <span className="text-[9px] text-slate-500 block uppercase tracking-wide">{out.label}</span>
                    <span className={`text-xs font-extrabold mt-1 block ${out.colorClass || 'text-slate-200'}`}>
                      {out.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
