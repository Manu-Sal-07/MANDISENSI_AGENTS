export type WorkflowStepId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export interface WorkflowStepConfig {
  id: WorkflowStepId;
  title: string;
  subtitle: string;
  duration: number; // in milliseconds
  description: string;
  statusText: string;
}

export interface AgentNodeConfig {
  label: string;
  actionText: string;
}

export interface AgentWorkflowConfig {
  agentName: string;
  agentId: WorkflowStepId;
  nodes: AgentNodeConfig[];
  outputs: { label: string; value: string; colorClass?: string }[];
}

export const workflowSteps: WorkflowStepConfig[] = [
  {
    id: 1,
    title: "Query Received",
    subtitle: "System Activated",
    duration: 2000,
    description: "Evaluator or system client initiates forecasting query request.",
    statusText: "Initializing engine context..."
  },
  {
    id: 2,
    title: "Loading Historical Data",
    subtitle: "Fetching Historical Series",
    duration: 2000,
    description: "Ingesting historical price series, trade volume metrics, and holiday/festival calendars.",
    statusText: "Syncing from memory caches..."
  },
  {
    id: 3,
    title: "Seasonality Agent Activated",
    subtitle: "Analyzing Seasonal Patterns",
    duration: 5000,
    description: "Extracting cyclical crop behaviors, annual patterns, and seasonal variations.",
    statusText: "Analyzing Seasonal Patterns"
  },
  {
    id: 4,
    title: "Arrival Volume Agent Activated",
    subtitle: "Analyzing Supply Conditions",
    duration: 5000,
    description: "Assessing mandi arrival counts, transportation delays, and harvest metrics.",
    statusText: "Analyzing Supply Conditions"
  },
  {
    id: 5,
    title: "External Factors Agent Activated",
    subtitle: "Analyzing External Signals",
    duration: 5000,
    description: "Analyzing macro indicators, weather developments, and consumer demand shifts.",
    statusText: "Analyzing External Signals"
  },
  {
    id: 6,
    title: "Meta Ensemble Activated",
    subtitle: "Combining Agent Outputs",
    duration: 10000, // 10 seconds for fusion and explanation visualizations
    description: "Weighting agent confidence signals through the ensemble model.",
    statusText: "Computing meta weights..."
  },
  {
    id: 7,
    title: "Decision Engine",
    subtitle: "Generating Final Forecast",
    duration: 2000,
    description: "Structuring prediction outputs and calculating confidence levels.",
    statusText: "Synthesizing intelligence telemetry..."
  },
  {
    id: 8,
    title: "Forecast Ready",
    subtitle: "Final Output Simulated",
    duration: 2000,
    description: "Final intelligence package compiled and visualized.",
    statusText: "Done"
  }
];

// Agent-level thinking configurations
export const seasonalityAgentConfig: AgentWorkflowConfig = {
  agentName: "Seasonality Agent",
  agentId: 3,
  nodes: [
    { label: "Historical Prices", actionText: "Retrieving daily prices..." },
    { label: "Trend Detection", actionText: "Extracting long-term movement..." },
    { label: "Seasonal Pattern Analysis", actionText: "Detecting recurring cycles..." },
    { label: "Festival Impact Detection", actionText: "Checking demand surges..." },
    { label: "Ensemble Prediction", actionText: "Combining seasonal models..." }
  ],
  outputs: [
    { label: "Trend", value: "Ascending", colorClass: "text-emerald-400" },
    { label: "Festival Impact", value: "High", colorClass: "text-sky-400" },
    { label: "Confidence", value: "82%", colorClass: "text-emerald-400" }
  ]
};

export const arrivalAgentConfig: AgentWorkflowConfig = {
  agentName: "Arrival Volume Agent",
  agentId: 4,
  nodes: [
    { label: "Arrival Volume Data", actionText: "Parsing truck unloading logs..." },
    { label: "Supply Stress Analysis", actionText: "Evaluating mandi stock buffers..." },
    { label: "Elasticity Estimation", actionText: "Calculating price responsiveness..." },
    { label: "Market Regime Detection", actionText: "Detecting supply bottleneck anomalies..." },
    { label: "Ensemble Prediction", actionText: "Solving volume probability density..." }
  ],
  outputs: [
    { label: "Supply Stress", value: "0.82", colorClass: "text-rose-400" },
    { label: "Regime", value: "Supply Squeeze", colorClass: "text-amber-400" },
    { label: "Confidence", value: "89%", colorClass: "text-emerald-400" }
  ]
};

export const externalAgentConfig: AgentWorkflowConfig = {
  agentName: "External Factors Agent",
  agentId: 5,
  nodes: [
    { label: "Weather Signals", actionText: "Syncing regional rainfall and temp indexes..." },
    { label: "News Signals", actionText: "Gleaning sentiment from agri newsfeeds..." },
    { label: "Policy Signals", actionText: "Scanning minimum support price (MSP) tariffs..." },
    { label: "Impact Scoring", actionText: "Aggregating external shock metrics..." },
    { label: "Signal Validation", actionText: "Cross-referencing historical correlation bounds..." }
  ],
  outputs: [
    { label: "Weather Impact", value: "Positive", colorClass: "text-emerald-400" },
    { label: "News Impact", value: "Neutral", colorClass: "text-slate-400" },
    { label: "Confidence", value: "74%", colorClass: "text-sky-400" }
  ]
};
