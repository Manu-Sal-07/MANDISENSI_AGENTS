import React from 'react';
import { History, ArrowRight } from 'lucide-react';

interface RecentQueriesProps {
  queries: string[];
  onClickQuery: (query: string) => void;
  isSimulating: boolean;
}

export default function RecentQueries({ queries, onClickQuery, isSimulating }: RecentQueriesProps) {
  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-2xl backdrop-blur-xl">
      
      {/* Title */}
      <div className="flex items-center gap-2 border-b border-slate-900 pb-3 mb-4">
        <div className="w-6 h-6 rounded bg-slate-900 border border-slate-800 flex items-center justify-center">
          <History className="w-3.5 h-3.5 text-slate-400" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono">
            Recent Queries
          </h4>
          <p className="text-[8px] text-slate-500 font-mono">SIMULATION_HISTORY_LOG</p>
        </div>
      </div>

      {/* Query List */}
      <div className="space-y-2 max-h-56 overflow-y-auto font-mono text-[9px] scrollbar-thin scrollbar-thumb-slate-900 scrollbar-track-transparent pr-1">
        {queries.length === 0 ? (
          <div className="text-slate-650 italic text-center py-4">
            [No recent queries recorded]
          </div>
        ) : (
          queries.map((query, idx) => (
            <button
              key={idx}
              disabled={isSimulating}
              onClick={() => onClickQuery(query)}
              className={`
                w-full text-left p-2.5 rounded-lg border border-slate-900 bg-slate-950/40 text-slate-400 hover:text-slate-200 hover:border-slate-800 hover:bg-slate-900/30 transition-all flex items-start gap-2 group active:scale-[0.99]
                disabled:opacity-50 disabled:pointer-events-none
              `}
            >
              <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-sky-400 shrink-0 transition-colors mt-0.5" />
              <span className="line-clamp-2 leading-relaxed">{query}</span>
            </button>
          ))
        )}
      </div>

    </div>
  );
}
