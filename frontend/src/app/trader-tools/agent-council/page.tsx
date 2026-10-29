'use client';

import ToolShell from '@/components/trader/ToolShell';
import CouncilDesk from '@/components/trader/CouncilDesk';

export default function Page() {
  return <ToolShell slug="agent-council">{({ commodity, mandiId }) => <CouncilDesk commodity={commodity} mandiId={mandiId} />}</ToolShell>;
}
