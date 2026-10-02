'use client';

import ToolShell from '@/components/trader/ToolShell';
import TransmissionMatrix from '@/components/trader/TransmissionMatrix';

export default function Page() {
  return <ToolShell slug="transmission">{(_focus) => <TransmissionMatrix />}</ToolShell>;
}
