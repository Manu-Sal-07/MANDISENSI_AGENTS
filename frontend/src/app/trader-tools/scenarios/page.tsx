'use client';

import ToolShell from '@/components/trader/ToolShell';
import ScenariosPanel from '@/components/trader/ScenariosPanel';

export default function Page() {
  return <ToolShell slug="scenarios">{({ commodity, mandiId }) => <ScenariosPanel commodity={commodity} mandiId={mandiId} />}</ToolShell>;
}
