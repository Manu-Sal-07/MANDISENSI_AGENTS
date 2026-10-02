import React from 'react';
import { WorkflowStepId } from '../workflowConfig';
import LiveOSDashboard from './LiveOSDashboard';

import { getMockAnalysis } from './MockAnalysisProvider';

interface WorkflowStepProps {
  stepId: WorkflowStepId;
  progress: number; // 0 to 100
}

export default function WorkflowStep({ stepId, progress }: WorkflowStepProps) {
  const defaultQuery = "Can I sell 5 tons of tomato in Kolar today?";
  const defaultResult = getMockAnalysis(defaultQuery);
  return (
    <LiveOSDashboard 
      stepId={stepId} 
      progress={progress} 
      queryText={defaultQuery} 
      tokens={defaultResult.parsed.tokens}
      analysisResult={defaultResult}
    />
  );
}
