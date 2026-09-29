import React from 'react';
import { Metadata } from 'next';
import { Activity, ShieldAlert, GraduationCap } from 'lucide-react';
import WorkflowContainer from '@/evaluator_demo/components/WorkflowContainer';

export const metadata: Metadata = {
  title: 'MandiSense AI | Evaluator Demonstration',
  description: 'Interactive visualization layer for evaluators detailing the multi-agent commodity forecasting pipeline.',
};

export default function EvaluatorDemoPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden font-sans">
      
      {/* Premium Cyber-Grid Background Layer */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#48d0ff_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)] bg-[size:100px_100px]" />
      
      {/* Ambient glowing blobs */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-sky-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Content Container */}
      <div className="container mx-auto px-4 py-8 flex-1 flex flex-col justify-start relative z-10">
        
        {/* Academic Presentation Header */}
        <header className="mb-8 border-b border-slate-900 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-400/20 uppercase font-mono">
                <GraduationCap className="w-3.5 h-3.5" />
                Evaluator Portal
              </span>
              <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-400/20 uppercase font-mono">
                Simulation Layer
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100 flex items-center gap-3">
              MandiSense AI
            </h1>
            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              Multi-Agent Forecasting Workflow Simulator. This interactive dashboard explains the internal cognitive agent pipeline execution and consensus resolution steps.
            </p>
          </div>

          <div className="flex items-center gap-3 bg-slate-950/60 border border-slate-900 px-4 py-2.5 rounded-lg text-slate-500 text-xs font-mono">
            <ShieldAlert className="w-4 h-4 text-amber-500/80" />
            <span>SANDBOX MODE: ISOLATED RUNTIME</span>
          </div>
        </header>

        {/* Workflow Component Workspace */}
        <main className="flex-1">
          <WorkflowContainer />
        </main>
      </div>
    </div>
  );
}
