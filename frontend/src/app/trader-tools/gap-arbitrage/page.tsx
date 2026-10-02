'use client';

import ToolShell from '@/components/trader/ToolShell';
import GapArbitrage from '@/components/trader/GapArbitrage';

export default function Page() {
  return <ToolShell slug="gap-arbitrage">{(_focus) => <GapArbitrage />}</ToolShell>;
}
