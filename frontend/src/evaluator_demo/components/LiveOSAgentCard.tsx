import React from 'react';
import { Shield, RefreshCw, Cpu, Activity } from 'lucide-react';

export type AgentType = 'seasonality' | 'arrival' | 'external';

interface LiveOSAgentCardProps {
  type: AgentType;
  stepId: number;
  progress: number;
  commodity?: string;
}

export default function LiveOSAgentCard({ type, stepId, progress, commodity }: LiveOSAgentCardProps) {
  // Determine if this agent is active, processing, or done
  const agentSteps = {
    seasonality: 3,
    arrival: 4,
    external: 5
  };

  const targetStep = agentSteps[type];
  const isAwaiting = stepId < targetStep;
  const isActive = stepId === targetStep;
  const isCompleted = stepId > targetStep;

  // Compute status text and color
  let statusText = "Awaiting Packets";
  let statusColor = "text-slate-650 border-slate-900 bg-slate-950/20";
  let showSpinner = false;
  let activeIcon = <Shield className="w-3.5 h-3.5 text-slate-600" />;

  if (isActive) {
    if (progress < 25) {
      statusText = "Receiving Inputs...";
      statusColor = "text-sky-400 border-sky-500/20 bg-sky-950/30 shadow-[0_0_10px_rgba(56,189,248,0.1)]";
      activeIcon = <Activity className="w-3.5 h-3.5 text-sky-400 animate-pulse" />;
    } else if (progress < 70) {
      statusText = "Processing...";
      statusColor = "text-amber-400 border-amber-500/20 bg-amber-950/30 shadow-[0_0_10px_rgba(245,158,11,0.1)]";
      showSpinner = true;
      activeIcon = <RefreshCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />;
    } else {
      statusText = "Generating Signals...";
      statusColor = "text-emerald-400 border-emerald-500/20 bg-emerald-950/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]";
      activeIcon = <Cpu className="w-3.5 h-3.5 text-emerald-400 animate-[pulse_1s_infinite]" />;
    }
  } else if (isCompleted) {
    statusText = "Active Signals";
    statusColor = "text-emerald-400 border-emerald-500/20 bg-emerald-950/40";
    activeIcon = <Cpu className="w-3.5 h-3.5 text-emerald-400" />;
  }

  const comm = commodity || "Tomato";

  const getSeasonalitySignals = () => {
    if (comm === "Onion") {
      return [
        { label: "Trend Cycle", value: "Trend ↑", valueColor: "text-emerald-400" },
        { label: "Festival Impact", value: "Festival -5%", valueColor: "text-rose-450" },
        { label: "Cycle Phase", value: "Low Season", valueColor: "text-slate-400" }
      ];
    }
    if (comm === "Potato") {
      return [
        { label: "Trend Cycle", value: "Trend ↓", valueColor: "text-rose-450" },
        { label: "Festival Impact", value: "Festival +10%", valueColor: "text-emerald-450" },
        { label: "Cycle Phase", value: "Normal Season", valueColor: "text-slate-400" }
      ];
    }
    if (comm === "Chilli") {
      return [
        { label: "Trend Cycle", value: "Trend ↑", valueColor: "text-emerald-400" },
        { label: "Festival Impact", value: "Festival +20%", valueColor: "text-emerald-400" },
        { label: "Cycle Phase", value: "Peak Demand", valueColor: "text-emerald-400" }
      ];
    }
    return [
      { label: "Trend Cycle", value: "Trend ↑", valueColor: "text-emerald-400" },
      { label: "Festival Impact", value: "Festival +8%", valueColor: "text-emerald-400" },
      { label: "Cycle Phase", value: "Cycle Peak", valueColor: "text-emerald-400" }
    ];
  };

  const getArrivalSignals = () => {
    if (comm === "Onion") {
      return [
        { label: "Supply Stress", value: "Stress 0.90", valueColor: "text-rose-450" },
        { label: "Elasticity", value: "Elas -0.65", valueColor: "text-amber-400" },
        { label: "Vol Shock", value: "Squeeze Alert", valueColor: "text-rose-450" }
      ];
    }
    if (comm === "Potato") {
      return [
        { label: "Supply Stress", value: "Stress 0.45", valueColor: "text-emerald-400" },
        { label: "Elasticity", value: "Elas -0.85", valueColor: "text-amber-400" },
        { label: "Vol Shock", value: "Normal Supply", valueColor: "text-emerald-400" }
      ];
    }
    if (comm === "Chilli") {
      return [
        { label: "Supply Stress", value: "Stress 0.70", valueColor: "text-amber-400" },
        { label: "Elasticity", value: "Elas -0.55", valueColor: "text-amber-400" },
        { label: "Vol Shock", value: "bottleneck", valueColor: "text-amber-400" }
      ];
    }
    return [
      { label: "Supply Stress", value: "Stress 0.82", valueColor: "text-amber-400" },
      { label: "Elasticity", value: "Elas -0.74", valueColor: "text-amber-400" },
      { label: "Vol Shock", value: "Shock Detected", valueColor: "text-amber-400" }
    ];
  };

  const getExternalSignals = () => {
    if (comm === "Onion") {
      return [
        { label: "Weather Forecast", value: "Adverse Weather", valueColor: "text-rose-450" },
        { label: "News Sentiment", value: "News Positive", valueColor: "text-emerald-400" },
        { label: "Trade Policy", value: "Policy Stable", valueColor: "text-slate-400" }
      ];
    }
    if (comm === "Potato") {
      return [
        { label: "Weather Forecast", value: "Favorable Weather", valueColor: "text-emerald-400" },
        { label: "News Sentiment", value: "News Negative", valueColor: "text-rose-450" },
        { label: "Trade Policy", value: "Tariff Shock", valueColor: "text-rose-450" }
      ];
    }
    if (comm === "Chilli") {
      return [
        { label: "Weather Forecast", value: "Severe Weather", valueColor: "text-rose-450" },
        { label: "News Sentiment", value: "News Positive", valueColor: "text-emerald-400" },
        { label: "Trade Policy", value: "Tariff Shock", valueColor: "text-rose-450" }
      ];
    }
    return [
      { label: "Weather Forecast", value: "Weather +", valueColor: "text-violet-400" },
      { label: "News Sentiment", value: "News Neutral", valueColor: "text-slate-400" },
      { label: "Trade Policy", value: "Policy Stable", valueColor: "text-violet-450" }
    ];
  };

  // Define details for each agent
  const agentDetails = {
    seasonality: {
      name: "Seasonality Agent",
      code: "SEASONALITY_COG_V12",
      themeColor: "text-emerald-400 border-emerald-500/10 hover:border-emerald-500/30",
      signals: getSeasonalitySignals()
    },
    arrival: {
      name: "Arrival Agent",
      code: "ARRIVAL_ELAS_V09",
      themeColor: "text-amber-400 border-amber-500/10 hover:border-amber-500/30",
      signals: getArrivalSignals()
    },
    external: {
      name: "External Agent",
      code: "EXTERNAL_EXT_V06",
      themeColor: "text-violet-400 border-violet-500/10 hover:border-violet-500/30",
      signals: getExternalSignals()
    }
  };

  const details = agentDetails[type];
  const showSignals = isCompleted || (isActive && progress >= 70);
  const showProcessingLoader = isActive && progress >= 25 && progress < 70;

  return (
    <div 
      className={`
        border rounded-xl p-4 bg-slate-950/80 transition-all duration-300 flex flex-col justify-between h-48 relative overflow-hidden
        ${isActive ? 'border-sky-500/40 shadow-[0_0_15px_rgba(56,189,248,0.08)]' : 'border-slate-900'}
      `}
    >
      {/* Background glow when active */}
      {isActive && (
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_10%,rgba(56,189,248,0.05),transparent_50%)] pointer-events-none" />
      )}

      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">{details.code}</span>
          <div className="flex items-center gap-1">
            <span className={`text-[8px] font-mono border px-2 py-0.5 rounded-full flex items-center gap-1.5 font-bold uppercase transition-all duration-300 ${statusColor}`}>
              {showSpinner && <RefreshCw className="w-2 h-2 animate-spin text-amber-400" />}
              {statusText}
            </span>
          </div>
        </div>

        <h4 className="text-xs font-bold text-slate-200 uppercase mt-2 tracking-wide flex items-center gap-2">
          {activeIcon}
          {details.name}
        </h4>
      </div>

      {/* Signal Fields Section */}
      <div className="space-y-1.5 my-3">
        {details.signals.map((sig, idx) => (
          <div key={idx} className="flex justify-between items-center text-[10px] font-mono py-0.5 border-b border-slate-900/60 pb-1">
            <span className="text-slate-500 text-[9px]">{sig.label}:</span>
            
            {showSignals ? (
              <span className={`font-bold animate-[fadeIn_0.3s_ease-out] ${sig.valueColor}`}>
                {sig.value}
              </span>
            ) : showProcessingLoader ? (
              <span className="text-amber-500/50 animate-pulse text-[9px]">ANALYZING...</span>
            ) : (
              <span className="text-slate-800 text-[9px]">---</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
