'use client';

import ToolShell from '@/components/trader/ToolShell';
import SpreadScanner from '@/components/trader/SpreadScanner';

export default function Page() {
  return <ToolShell slug="spreads">{(_focus) => <SpreadScanner />}</ToolShell>;
}
