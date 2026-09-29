import React from 'react';
import { Compass, RefreshCw } from 'lucide-react';
import { ParsedQuery } from './MockAnalysisProvider';

interface QueryParserAnimationProps {
  progress: number;
  parsed: ParsedQuery;
  queryText: string;
}

export default function QueryParserAnimation({ progress, parsed, queryText }: QueryParserAnimationProps) {
  const fields = [
    { label: "Commodity", value: parsed.commodity, trigger: 20 },
    { label: "Market", value: parsed.market, trigger: 40 },
    { label: "Intent", value: parsed.intent, trigger: 60 },
    { label: "Quantity", value: parsed.quantity, trigger: 80 },
    { label: "Horizon", value: parsed.horizon, trigger: 95 }
  ];

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-2xl backdrop-blur-md space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-900/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-sky-950/50 border border-sky-400/20 flex items-center justify-center">
            <Compass className="w-3.5 h-3.5 text-sky-400 animate-spin" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono">
              Understanding Query...
            </h4>
            <p className="text-[8px] text-slate-500 font-mono">NLP_COGNITIVE_PARSER_ACTIVE</p>
          </div>
        </div>
        
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-sky-400">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span>Tokenizing</span>
        </div>
      </div>

      {/* Raw input text bubble */}
      <div className="bg-slate-900/30 border border-slate-900 rounded-lg p-3 font-mono text-[10px] text-slate-300">
        <span className="text-slate-550 uppercase text-[8px] block font-bold tracking-wider mb-1">Raw User Query:</span>
        <span className="italic">"{queryText}"</span>
      </div>

      {/* Structured Token Extraction Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2 font-mono text-[9px]">
        {fields.map((field, idx) => {
          const isExtracted = progress >= field.trigger;
          return (
            <div 
              key={idx}
              className={`
                border rounded-lg p-3 flex flex-col justify-between h-20 transition-all duration-500
                ${isExtracted 
                  ? 'border-sky-500/30 bg-sky-950/15 text-sky-350 shadow-[0_0_12px_rgba(56,189,248,0.05)] translate-y-0 opacity-100' 
                  : 'border-slate-900 bg-transparent text-slate-700 translate-y-1 opacity-20'
                }
              `}
            >
              <span className="text-slate-500 uppercase font-bold text-[8px] tracking-wider">{field.label}</span>
              <span className={`text-[10px] font-bold mt-2 ${isExtracted ? 'text-sky-400' : 'text-slate-750'}`}>
                {isExtracted ? field.value : '...'}
              </span>
            </div>
          );
        })}
      </div>

    </div>
  );
}
