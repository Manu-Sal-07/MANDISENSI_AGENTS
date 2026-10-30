'use client';

import ToolShell from '@/components/trader/ToolShell';
import ReportingValue from '@/components/trader/ReportingValue';

export default function Page() {
  return <ToolShell slug="reporting-value">{(_focus) => <ReportingValue />}</ToolShell>;
}
