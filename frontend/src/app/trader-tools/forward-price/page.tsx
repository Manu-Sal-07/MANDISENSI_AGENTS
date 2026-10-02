'use client';

import ToolShell from '@/components/trader/ToolShell';
import ForwardPriceCalculator from '@/components/trader/ForwardPriceCalculator';

export default function Page() {
  return <ToolShell slug="forward-price">{({ commodity, mandiId }) => <ForwardPriceCalculator commodity={commodity} mandiId={mandiId} />}</ToolShell>;
}
