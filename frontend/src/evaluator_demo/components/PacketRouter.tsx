import React from 'react';
import DataPacket from './DataPacket';
import SignalPacket from './SignalPacket';

interface PacketRouterProps {
  stepId: number;
  progress: number;
  tokens: string[];
}

// Quadratic Bezier interpolation
function getBezierPoint(t: number, start: { x: number; y: number }, control: { x: number; y: number }, end: { x: number; y: number }) {
  const x = (1 - t) * (1 - t) * start.x + 2 * (1 - t) * t * control.x + t * t * end.x;
  const y = (1 - t) * (1 - t) * start.y + 2 * (1 - t) * t * control.y + t * t * end.y;
  return { x, y };
}

export default function PacketRouter({ stepId, progress, tokens }: PacketRouterProps) {
  // Coordinates in percentage
  const queryNode = { x: 50, y: 12 };
  
  const seasonalityAgent = { x: 15, y: 45 };
  const arrivalAgent = { x: 50, y: 45 };
  const externalAgent = { x: 85, y: 45 };

  const fusionChamber = { x: 50, y: 78 };

  // Control points for bezier curves
  const qToSControl = { x: 28, y: 15 };
  const qToAControl = { x: 50, y: 28 };
  const qToEControl = { x: 72, y: 15 };

  const sToFControl = { x: 28, y: 68 };
  const aToFControl = { x: 50, y: 62 };
  const eToFControl = { x: 72, y: 68 };

  const commodity = tokens[0] || "Tomato";
  const market = tokens[1] || "Kolar";
  const intent = tokens[2] || "Sell";
  const horizon = tokens[tokens.length - 1] || "Today";

  // Helper to get t parameter for staggered packets
  const getStaggeredT = (prog: number, startDelay: number, duration: number) => {
    if (prog < startDelay) return 0;
    return Math.min(1, (prog - startDelay) / duration);
  };

  // Render step 3 (Data Packets -> Seasonality)
  const renderStep3Packets = () => {
    if (stepId !== 3) return null;
    const p1Label = commodity;
    const p2Label = intent;
    const p3Label = horizon;

    const t1 = getStaggeredT(progress, 0, 30);
    const t2 = getStaggeredT(progress, 8, 30);
    const t3 = getStaggeredT(progress, 16, 30);

    const pos1 = getBezierPoint(t1, queryNode, qToSControl, seasonalityAgent);
    const pos2 = getBezierPoint(t2, queryNode, qToSControl, seasonalityAgent);
    const pos3 = getBezierPoint(t3, queryNode, qToSControl, seasonalityAgent);

    return (
      <>
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none transition-opacity duration-150" style={{ left: `${pos1.x}%`, top: `${pos1.y}%` }}>
            <DataPacket label={p1Label} />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none transition-opacity duration-150" style={{ left: `${pos2.x}%`, top: `${pos2.y}%` }}>
            <DataPacket label={p2Label} />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none transition-opacity duration-150" style={{ left: `${pos3.x}%`, top: `${pos3.y}%` }}>
            <DataPacket label={p3Label} />
          </div>
        )}
      </>
    );
  };

  // Render step 4 (Data Packets -> Arrival)
  const renderStep4Packets = () => {
    if (stepId !== 4) return null;
    const p1Label = commodity;
    const p2Label = market;
    const p3Label = tokens.length > 4 ? tokens[3] : "1 Ton";

    const t1 = getStaggeredT(progress, 0, 30);
    const t2 = getStaggeredT(progress, 8, 30);
    const t3 = getStaggeredT(progress, 16, 30);

    const pos1 = getBezierPoint(t1, queryNode, qToAControl, arrivalAgent);
    const pos2 = getBezierPoint(t2, queryNode, qToAControl, arrivalAgent);
    const pos3 = getBezierPoint(t3, queryNode, qToAControl, arrivalAgent);

    return (
      <>
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos1.x}%`, top: `${pos1.y}%` }}>
            <DataPacket label={p1Label} />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos2.x}%`, top: `${pos2.y}%` }}>
            <DataPacket label={p2Label} />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos3.x}%`, top: `${pos3.y}%` }}>
            <DataPacket label={p3Label} />
          </div>
        )}
      </>
    );
  };

  // Render step 5 (Data Packets -> External)
  const renderStep5Packets = () => {
    if (stepId !== 5) return null;
    const p1Label = commodity;
    const p2Label = market;
    const p3Label = horizon;

    const t1 = getStaggeredT(progress, 0, 30);
    const t2 = getStaggeredT(progress, 8, 30);
    const t3 = getStaggeredT(progress, 16, 30);

    const pos1 = getBezierPoint(t1, queryNode, qToEControl, externalAgent);
    const pos2 = getBezierPoint(t2, queryNode, qToEControl, externalAgent);
    const pos3 = getBezierPoint(t3, queryNode, qToEControl, externalAgent);

    return (
      <>
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos1.x}%`, top: `${pos1.y}%` }}>
            <DataPacket label={p1Label} />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos2.x}%`, top: `${pos2.y}%` }}>
            <DataPacket label={p2Label} />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${pos3.x}%`, top: `${pos3.y}%` }}>
            <DataPacket label={p3Label} />
          </div>
        )}
      </>
    );
  };

  // Render step 6 (Signal Packets -> Fusion Node)
  const renderStep6Packets = () => {
    if (stepId !== 6 || progress >= 40) return null;

    // Stagger parameters
    const t1 = getStaggeredT(progress, 0, 22);
    const t2 = getStaggeredT(progress, 7, 22);
    const t3 = getStaggeredT(progress, 14, 22);

    // Seasonality coordinates
    const sPos1 = getBezierPoint(t1, seasonalityAgent, sToFControl, fusionChamber);
    const sPos2 = getBezierPoint(t2, seasonalityAgent, sToFControl, fusionChamber);
    const sPos3 = getBezierPoint(t3, seasonalityAgent, sToFControl, fusionChamber);

    // Arrival coordinates
    const aPos1 = getBezierPoint(t1, arrivalAgent, aToFControl, fusionChamber);
    const aPos2 = getBezierPoint(t2, arrivalAgent, aToFControl, fusionChamber);
    const aPos3 = getBezierPoint(t3, arrivalAgent, aToFControl, fusionChamber);

    // External coordinates
    const ePos1 = getBezierPoint(t1, externalAgent, eToFControl, fusionChamber);
    const ePos2 = getBezierPoint(t2, externalAgent, eToFControl, fusionChamber);
    const ePos3 = getBezierPoint(t3, externalAgent, eToFControl, fusionChamber);

    // Dynamic signal labels lookup
    let sSig = ["Trend ↑", "Festival +8%", "Cycle Peak"];
    let aSig = ["Stress 0.82", "Elasticity -0.74", "Supply Shock"];
    let eSig = ["Weather +", "News Neutral", "Policy OK"];

    if (commodity === "Onion") {
      sSig = ["Trend ↑", "Festival -5%", "Low Season"];
      aSig = ["Stress 0.90", "Elasticity -0.65", "Squeeze Alert"];
      eSig = ["Weather Adverse", "News Positive", "Policy OK"];
    } else if (commodity === "Potato") {
      sSig = ["Trend ↓", "Festival +10%", "Normal Season"];
      aSig = ["Stress 0.45", "Elasticity -0.85", "Normal Supply"];
      eSig = ["Weather Favorable", "News Negative", "Tariff Shock"];
    } else if (commodity === "Chilli") {
      sSig = ["Trend ↑", "Festival +20%", "Peak Demand"];
      aSig = ["Stress 0.70", "Elasticity -0.55", "bottleneck"];
      eSig = ["Severe Weather", "News Positive", "Tariff Shock"];
    }

    return (
      <>
        {/* Seasonality signals */}
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${sPos1.x}%`, top: `${sPos1.y}%` }}>
            <SignalPacket label={sSig[0]} theme="emerald" />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${sPos2.x}%`, top: `${sPos2.y}%` }}>
            <SignalPacket label={sSig[1]} theme="emerald" />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${sPos3.x}%`, top: `${sPos3.y}%` }}>
            <SignalPacket label={sSig[2]} theme="emerald" />
          </div>
        )}

        {/* Arrival signals */}
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${aPos1.x}%`, top: `${aPos1.y}%` }}>
            <SignalPacket label={aSig[0]} theme="amber" />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${aPos2.x}%`, top: `${aPos2.y}%` }}>
            <SignalPacket label={aSig[1]} theme="amber" />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${aPos3.x}%`, top: `${aPos3.y}%` }}>
            <SignalPacket label={aSig[2]} theme="amber" />
          </div>
        )}

        {/* External signals */}
        {t1 > 0 && t1 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${ePos1.x}%`, top: `${ePos1.y}%` }}>
            <SignalPacket label={eSig[0]} theme="violet" />
          </div>
        )}
        {t2 > 0 && t2 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${ePos2.x}%`, top: `${ePos2.y}%` }}>
            <SignalPacket label={eSig[1]} theme="violet" />
          </div>
        )}
        {t3 > 0 && t3 < 1 && (
          <div className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none" style={{ left: `${ePos3.x}%`, top: `${ePos3.y}%` }}>
            <SignalPacket label={eSig[2]} theme="violet" />
          </div>
        )}
      </>
    );
  };

  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none z-10">
      {/* Background SVG Grid Connectors */}
      <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        {/* Top to Middle paths */}
        <path 
          d={`M ${queryNode.x} ${queryNode.y} Q ${qToSControl.x} ${qToSControl.y} ${seasonalityAgent.x} ${seasonalityAgent.y}`} 
          fill="none" 
          stroke={stepId === 3 ? "rgba(56,189,248,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 3 ? "2" : "1"} 
          strokeDasharray={stepId === 3 ? "5 3" : "4 4"}
          className={stepId === 3 ? "animate-[pulse_1s_infinite]" : ""}
        />
        <path 
          d={`M ${queryNode.x} ${queryNode.y} Q ${qToAControl.x} ${qToAControl.y} ${arrivalAgent.x} ${arrivalAgent.y}`} 
          fill="none" 
          stroke={stepId === 4 ? "rgba(56,189,248,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 4 ? "2" : "1"} 
          strokeDasharray={stepId === 4 ? "5 3" : "4 4"}
          className={stepId === 4 ? "animate-[pulse_1s_infinite]" : ""}
        />
        <path 
          d={`M ${queryNode.x} ${queryNode.y} Q ${qToEControl.x} ${qToEControl.y} ${externalAgent.x} ${externalAgent.y}`} 
          fill="none" 
          stroke={stepId === 5 ? "rgba(56,189,248,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 5 ? "2" : "1"} 
          strokeDasharray={stepId === 5 ? "5 3" : "4 4"}
          className={stepId === 5 ? "animate-[pulse_1s_infinite]" : ""}
        />

        {/* Middle to Bottom paths */}
        <path 
          d={`M ${seasonalityAgent.x} ${seasonalityAgent.y} Q ${sToFControl.x} ${sToFControl.y} ${fusionChamber.x} ${fusionChamber.y}`} 
          fill="none" 
          stroke={stepId === 6 ? "rgba(16,185,129,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 6 ? "2" : "1"} 
          strokeDasharray={stepId === 6 ? "5 3" : "4 4"}
          className={stepId === 6 ? "animate-[pulse_1s_infinite]" : ""}
        />
        <path 
          d={`M ${arrivalAgent.x} ${arrivalAgent.y} Q ${aToFControl.x} ${aToFControl.y} ${fusionChamber.x} ${fusionChamber.y}`} 
          fill="none" 
          stroke={stepId === 6 ? "rgba(245,158,11,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 6 ? "2" : "1"} 
          strokeDasharray={stepId === 6 ? "5 3" : "4 4"}
          className={stepId === 6 ? "animate-[pulse_1s_infinite]" : ""}
        />
        <path 
          d={`M ${externalAgent.x} ${externalAgent.y} Q ${eToFControl.x} ${eToFControl.y} ${fusionChamber.x} ${fusionChamber.y}`} 
          fill="none" 
          stroke={stepId === 6 ? "rgba(139,92,246,0.4)" : "rgba(30,41,59,0.5)"} 
          strokeWidth={stepId === 6 ? "2" : "1"} 
          strokeDasharray={stepId === 6 ? "5 3" : "4 4"}
          className={stepId === 6 ? "animate-[pulse_1s_infinite]" : ""}
        />
      </svg>

      {/* Render flying packets based on active step */}
      {renderStep3Packets()}
      {renderStep4Packets()}
      {renderStep5Packets()}
      {renderStep6Packets()}
    </div>
  );
}
