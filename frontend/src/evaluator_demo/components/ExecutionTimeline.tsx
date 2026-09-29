import React, { useEffect, useState, useRef } from 'react';
import { Terminal } from 'lucide-react';

interface ExecutionTimelineProps {
  stepId: number;
  progress: number;
}

interface LogEntry {
  time: string;
  source: 'SYSTEM' | 'AGENT' | 'FUSION' | 'DECISION' | 'FORECAST';
  message: string;
}

export default function ExecutionTimeline({ stepId, progress }: ExecutionTimelineProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom of logs
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Construct running log entries based on stepId and progress
  useEffect(() => {
    const fullLogConfig: { triggerStep: number; triggerProgress: number; log: LogEntry }[] = [
      {
        triggerStep: 1,
        triggerProgress: 0,
        log: { time: "09:31:01", source: "SYSTEM", message: "INGESTION: Received raw natural language query: 'Can I sell 5 tons of tomato in Kolar today?'" }
      },
      {
        triggerStep: 1,
        triggerProgress: 30,
        log: { time: "09:31:01", source: "SYSTEM", message: "NLP_PARSER: Activating token extraction matrix..." }
      },
      {
        triggerStep: 2,
        triggerProgress: 0,
        log: { time: "09:31:02", source: "SYSTEM", message: "NLP_PARSER: Extracted tokens: [Tomato], [Kolar], [Sell], [5 Tons], [Today]" }
      },
      {
        triggerStep: 2,
        triggerProgress: 40,
        log: { time: "09:31:02", source: "SYSTEM", message: "DATA_SERVICE: Fetching 365-day historical price series for Latur/Kolar tomatoes..." }
      },
      {
        triggerStep: 3,
        triggerProgress: 0,
        log: { time: "09:31:03", source: "AGENT", message: "SEASONALITY: Inputs received. Initiating trend analysis and cyclical detection..." }
      },
      {
        triggerStep: 3,
        triggerProgress: 60,
        log: { time: "09:31:03", source: "AGENT", message: "SEASONALITY: Extracted Trend ↑, Festival +8%, Cycle Peak." }
      },
      {
        triggerStep: 4,
        triggerProgress: 0,
        log: { time: "09:31:03", source: "AGENT", message: "ARRIVAL: Inputs received. Starting market supply elasticity & elasticity model..." }
      },
      {
        triggerStep: 4,
        triggerProgress: 60,
        log: { time: "09:31:04", source: "AGENT", message: "ARRIVAL: Elasticity profile generated: Supply Stress 0.82, Elasticity -0.74, Shock Detected." }
      },
      {
        triggerStep: 5,
        triggerProgress: 0,
        log: { time: "09:31:04", source: "AGENT", message: "EXTERNAL: Inputs received. Analyzing current local news sentiment & weather forecasts..." }
      },
      {
        triggerStep: 5,
        triggerProgress: 60,
        log: { time: "09:31:05", source: "AGENT", message: "EXTERNAL: Signals compiled: Weather Positive, News Neutral, Policy Stable." }
      },
      {
        triggerStep: 6,
        triggerProgress: 0,
        log: { time: "09:31:06", source: "FUSION", message: "METAFUSION: Multi-Agent run completed. Routing 9 distinct signals to Meta Ensemble chamber..." }
      },
      {
        triggerStep: 6,
        triggerProgress: 40,
        log: { time: "09:31:07", source: "FUSION", message: "METAFUSION: Orbiting signals and computing meta-weights attribution mapping..." }
      },
      {
        triggerStep: 7,
        triggerProgress: 0,
        log: { time: "09:31:08", source: "DECISION", message: "DECISION_ENGINE: Aggregating weights (Arrival 46%, Seasonality 38%, External 16%)..." }
      },
      {
        triggerStep: 7,
        triggerProgress: 50,
        log: { time: "09:31:08", source: "DECISION", message: "DECISION_ENGINE: Live consensus score resolved: 84/100." }
      },
      {
        triggerStep: 8,
        triggerProgress: 0,
        log: { time: "09:31:10", source: "FORECAST", message: "FORECAST: Recommendation generated successfully: SELL TODAY (+6.2% expected change, 84% confidence)." }
      }
    ];

    // Filter logs that should have triggered by now
    const activeLogs = fullLogConfig
      .filter(item => {
        if (item.triggerStep < stepId) return true;
        if (item.triggerStep === stepId && item.triggerProgress <= progress) return true;
        return false;
      })
      .map(item => item.log);

    setLogs(activeLogs);
  }, [stepId, progress]);

  const sourceColors = {
    SYSTEM: "text-sky-400 bg-sky-950/40 border-sky-900/50",
    AGENT: "text-emerald-400 bg-emerald-950/40 border-emerald-900/50",
    FUSION: "text-amber-400 bg-amber-950/40 border-amber-900/50",
    DECISION: "text-violet-400 bg-violet-950/40 border-violet-900/50",
    FORECAST: "text-rose-400 bg-rose-950/40 border-rose-900/50"
  };

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl overflow-hidden shadow-2xl backdrop-blur-md flex flex-col h-40">
      
      {/* Terminal Title Bar */}
      <div className="bg-slate-900/90 border-b border-slate-950 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Simulated Mac OS Style buttons */}
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>
          <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1.5 ml-2">
            <Terminal className="w-3 h-3 text-slate-500" />
            TELEMETRY_LOG_SYSTEM
          </span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-slate-600">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          LIVE_STREAMING
        </div>
      </div>

      {/* Terminal Log Console */}
      <div className="flex-1 p-3 overflow-y-auto font-mono text-[10px] space-y-2 scrollbar-thin scrollbar-thumb-slate-900 scrollbar-track-transparent">
        {logs.length === 0 ? (
          <div className="text-slate-650 flex items-center justify-center h-full animate-pulse">
            [WAITING FOR SYSTEM EXECUTION LOGS...]
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-2.5 leading-relaxed text-slate-300 animate-[fadeIn_0.2s_ease-out]">
              <span className="text-slate-500 shrink-0">[{log.time}]</span>
              <span className={`text-[8px] font-extrabold px-1.5 py-0.2 rounded border shrink-0 ${sourceColors[log.source]}`}>
                {log.source}
              </span>
              <span className="font-medium">{log.message}</span>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>

    </div>
  );
}
