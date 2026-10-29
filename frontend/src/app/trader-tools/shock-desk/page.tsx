'use client';

import ToolShell from '@/components/trader/ToolShell';
import ShockDesk from '@/components/trader/ShockDesk';

export default function Page() {
  return <ToolShell slug="shock-desk">{(_focus) => <ShockDesk />}</ToolShell>;
}
