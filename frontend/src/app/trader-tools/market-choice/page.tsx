'use client';

import ToolShell from '@/components/trader/ToolShell';
import MarketChoiceDesk from '@/components/trader/MarketChoiceDesk';

export default function Page() {
  return <ToolShell slug="market-choice">{(_focus) => <MarketChoiceDesk />}</ToolShell>;
}
