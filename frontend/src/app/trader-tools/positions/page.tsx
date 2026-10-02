'use client';

import ToolShell, { useDeskMandis } from '@/components/trader/ToolShell';
import PositionBook from '@/components/trader/PositionBook';

export default function Page() {
  const mandis = useDeskMandis();
  return <ToolShell slug="positions">{(_focus) => <PositionBook mandis={mandis} />}</ToolShell>;
}
