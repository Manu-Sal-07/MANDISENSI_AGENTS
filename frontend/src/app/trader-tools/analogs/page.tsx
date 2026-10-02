'use client';

import ToolShell from '@/components/trader/ToolShell';
import AnalogsPanel from '@/components/trader/AnalogsPanel';

export default function Page() {
  return <ToolShell slug="analogs">{({ commodity, mandiId }) => <AnalogsPanel commodity={commodity} mandiId={mandiId} />}</ToolShell>;
}
