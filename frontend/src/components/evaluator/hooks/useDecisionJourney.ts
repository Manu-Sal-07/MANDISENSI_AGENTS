'use client';

import { useState, useEffect, useRef } from 'react';

export type AgentId = 'seasonality' | 'arrival' | 'external' | 'ensemble' | null;

export type JourneyState =
  | 'IDLE'
  | 'OFFLINE_FACTORY'
  | 'MODEL_REGISTRY'
  | 'LIVE_INGESTION'
  | 'LOCATION_INTELLIGENCE'
  | 'DATA_PROCESSING'
  | 'DIGITAL_TWIN'
  | 'SEASONALITY_ANALYSIS'
  | 'ARRIVAL_ANALYSIS'
  | 'EXTERNAL_ANALYSIS'
  | 'META_ENSEMBLE'
  | 'DECISION_ENGINE'
  | 'INFRA_DISCOVERY'
  | 'FINAL_RECOMMENDATION'
  | 'COMPLETE';

export const STATES_SEQUENCE: JourneyState[] = [
  'IDLE',
  'OFFLINE_FACTORY',
  'MODEL_REGISTRY',
  'LIVE_INGESTION',
  'LOCATION_INTELLIGENCE',
  'DATA_PROCESSING',
  'DIGITAL_TWIN',
  'SEASONALITY_ANALYSIS',
  'ARRIVAL_ANALYSIS',
  'EXTERNAL_ANALYSIS',
  'META_ENSEMBLE',
  'DECISION_ENGINE',
  'INFRA_DISCOVERY',
  'FINAL_RECOMMENDATION',
  'COMPLETE',
];

const STATE_DURATIONS: Record<JourneyState, number> = {
  IDLE: 0,
  OFFLINE_FACTORY: 2000,
  MODEL_REGISTRY: 1500,
  LIVE_INGESTION: 2000,
  LOCATION_INTELLIGENCE: 2000,
  DATA_PROCESSING: 1500,
  DIGITAL_TWIN: 2000,
  SEASONALITY_ANALYSIS: 2500,
  ARRIVAL_ANALYSIS: 2500,
  EXTERNAL_ANALYSIS: 2500,
  META_ENSEMBLE: 3000,
  DECISION_ENGINE: 2500,
  INFRA_DISCOVERY: 2000,
  FINAL_RECOMMENDATION: 4000,
  COMPLETE: 0,
};

// Log messages matching the requirements for each state
const STATE_LOGS: Record<JourneyState, string[]> = {
  IDLE: ['Ready to initiate evaluator simulation... Click Run to start.'],
  OFFLINE_FACTORY: [
    'Initializing Offline Intelligence Factory...',
    'Loading trained models from historical datasets...',
    'Analyzing Agmarknet Data (5-year price history)...',
    'Ingesting Weather History & government policy MSP models...',
  ],
  MODEL_REGISTRY: [
    'Model Registry Connected.',
    'Verifying weights for sub-agents (Seasonality, Arrival, External).',
    'Registry validated. Loading weights into runtime memory.',
  ],
  LIVE_INGESTION: [
    'Live Ingestion Activated.',
    'Weather API state -> active',
    'Market Data feed state -> active',
    'Govt Policies checker state -> active',
    'Satellite Data stream state -> active',
  ],
  LOCATION_INTELLIGENCE: [
    'Location Intelligence running...',
    'Resolving Farmer Location (Geo-coordinates fixed).',
    'Mapping Nearby Mandis...',
    'Finding Warehouses & cold storages in 50km radius.',
  ],
  DATA_PROCESSING: [
    'Live Data Processing running...',
    'Normalizing raw feeds...',
    'Calculating crop volatility indicators & short-term trend coefficients.',
  ],
  DIGITAL_TWIN: [
    'Digital Farmer Twin building...',
    'Building Farmer Context...',
    'Crop Profile Loaded (Tomato, 5 Tons, Kolar).',
    'Market Context Loaded (High price stress).',
    'Weather Context Loaded (Expected dry spell).',
    'Scheme Eligibility and Infrastructure access mapped.',
  ],
  SEASONALITY_ANALYSIS: [
    'Seasonality Agent activated.',
    'Analyzing Historical Cycles...',
    'Validating seasonality models (9 sub-models)...',
    'Confidence Building... Seasonality index computed.',
    'Seasonality Agent Completed.',
  ],
  ARRIVAL_ANALYSIS: [
    'Arrival Agent activated.',
    'Analyzing Supply Stress...',
    'Detecting Arrival Trends (8 sub-models)...',
    'Validating supply contraction patterns...',
    'Arrival Agent Completed.',
  ],
  EXTERNAL_ANALYSIS: [
    'External Factors Agent activated.',
    'Analyzing External Signals (Macro indices, Fuel prices, MSP)...',
    'Evaluating Impact (6 sub-models)...',
    'External Factors Agent Completed.',
  ],
  META_ENSEMBLE: [
    'Meta Ensemble activated.',
    'Combining Agent Outputs...',
    'Applying Dynamic Weighting (Regime: High Contraction)...',
    'Computing Confidence Fusion scores...',
    'Integrated intelligence weightings generated.',
  ],
  DECISION_ENGINE: [
    'Decision Engine executing...',
    'Running Conflict Resolution...',
    'Performing Risk Assessment...',
    'Explainability Logs Generation...',
    'Decision Ready.',
  ],
  INFRA_DISCOVERY: [
    'Infrastructure Discovery active...',
    'Nearest Mandi identified (Kolar Mandi: 12km).',
    'Cold Storage identified (Kolar Cold Storage Co: 18km).',
    'Warehouse and FPO facilities resolved.',
  ],
  FINAL_RECOMMENDATION: [
    'Synthesizing final recommendation...',
    'RECOMMENDATION: HOLD TOMATO FOR 7 DAYS',
    'Confidence: 84%',
    'Expected Gain: ₹250 / Quintal',
  ],
  COMPLETE: [
    'Decision Journey Completed successfully.',
    'All agent telemetry files registered and ready for evaluation.',
  ],
};

export function useDecisionJourney() {
  const [currentState, setCurrentState] = useState<JourneyState>('IDLE');
  const [isSimulating, setIsSimulating] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [stepProgress, setStepProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>(STATE_LOGS.IDLE);

  const requestRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const elapsedBeforePauseRef = useRef<number>(0);

  // Sequences
  const currentStateIndex = STATES_SEQUENCE.indexOf(currentState);

  // Transition to a specific state and accumulate logs
  const transitionToState = (state: JourneyState) => {
    setCurrentState(state);
    
    // Accumulate logs from all completed states up to the new state
    const newLogs: string[] = [];
    const targetIdx = STATES_SEQUENCE.indexOf(state);
    
    for (let i = 1; i <= targetIdx; i++) {
      const s = STATES_SEQUENCE[i];
      newLogs.push(...STATE_LOGS[s]);
    }
    
    // If IDLE, show initial logs
    if (state === 'IDLE') {
      setLogs(STATE_LOGS.IDLE);
    } else {
      setLogs(newLogs);
    }
  };

  const runJourney = () => {
    if (currentState === 'COMPLETE') {
      transitionToState('OFFLINE_FACTORY');
    } else if (currentState === 'IDLE') {
      transitionToState('OFFLINE_FACTORY');
    }
    setIsSimulating(true);
    setIsPaused(false);
    startTimeRef.current = null;
  };

  const pauseJourney = () => {
    setIsSimulating(false);
    setIsPaused(true);
    if (requestRef.current) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    }
  };

  const resetJourney = () => {
    setIsSimulating(false);
    setIsPaused(false);
    setStepProgress(0);
    elapsedBeforePauseRef.current = 0;
    startTimeRef.current = null;
    transitionToState('IDLE');
    if (requestRef.current) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    }
  };

  const replayJourney = () => {
    setIsSimulating(false);
    setIsPaused(false);
    setStepProgress(0);
    elapsedBeforePauseRef.current = 0;
    startTimeRef.current = null;
    if (requestRef.current) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    }
    setTimeout(() => {
      transitionToState('OFFLINE_FACTORY');
      setIsSimulating(true);
    }, 50);
  };

  // State loop manager
  useEffect(() => {
    if (!isSimulating || currentState === 'IDLE' || currentState === 'COMPLETE') {
      return;
    }

    const duration = STATE_DURATIONS[currentState];

    const animate = (time: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = time;
      }

      const elapsed = (time - startTimeRef.current) + elapsedBeforePauseRef.current;
      const progressPercent = Math.min((elapsed / duration) * 100, 100);

      setStepProgress(progressPercent);

      if (elapsed >= duration) {
        // Step finished, go to next state
        const nextIdx = currentStateIndex + 1;
        const nextState = STATES_SEQUENCE[nextIdx];

        if (nextState) {
          setStepProgress(0);
          startTimeRef.current = null;
          elapsedBeforePauseRef.current = 0;
          transitionToState(nextState);
          
          if (nextState === 'COMPLETE') {
            setIsSimulating(false);
          }
        }
      } else {
        requestRef.current = requestAnimationFrame(animate);
      }
    };

    requestRef.current = requestAnimationFrame(animate);

    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      if (startTimeRef.current) {
        const now = performance.now();
        elapsedBeforePauseRef.current += (now - startTimeRef.current);
        startTimeRef.current = null;
      }
    };
  }, [isSimulating, currentState, currentStateIndex]);

  return {
    currentState,
    isSimulating,
    isPaused,
    stepProgress,
    runJourney,
    pauseJourney,
    resetJourney,
    replayJourney,
    logs,
    currentStateIndex,
  };
}
