'use client';

import ToolShell from '@/components/trader/ToolShell';
import ForecastAudit from '@/components/trader/ForecastAudit';

export default function Page() {
  return <ToolShell slug="forecast-audit">{(_focus) => <ForecastAudit />}</ToolShell>;
}
