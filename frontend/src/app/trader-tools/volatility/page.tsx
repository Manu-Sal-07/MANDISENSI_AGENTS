'use client';

import ToolShell from '@/components/trader/ToolShell';
import VolatilityPanel from '@/components/trader/VolatilityPanel';

export default function Page() {
  return <ToolShell slug="volatility">{({ commodity, mandiId }) => <VolatilityPanel commodity={commodity} mandiId={mandiId} />}</ToolShell>;
}
