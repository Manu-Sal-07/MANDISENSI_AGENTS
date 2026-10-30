'use client';

import ToolShell from '@/components/trader/ToolShell';
import CrowdSimulator from '@/components/trader/CrowdSimulator';

export default function Page() {
  return <ToolShell slug="crowd-simulator">{(_focus) => <CrowdSimulator />}</ToolShell>;
}
