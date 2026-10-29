'use client';

import ToolShell from '@/components/trader/ToolShell';
import FloorMonitor from '@/components/trader/FloorMonitor';

export default function Page() {
  return <ToolShell slug="floor-monitor">{(_focus) => <FloorMonitor />}</ToolShell>;
}
