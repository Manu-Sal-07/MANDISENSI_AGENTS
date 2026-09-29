'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * The shared "this feature has nothing to say yet" state.
 *
 * Every tool in this package can honestly return UNAVAILABLE (or a more
 * specific refusal status) instead of data — see each endpoint's module
 * docstring in `mandisense_ai/farmer/`. Rendered identically everywhere
 * rather than as a bespoke empty-state per panel, so "no data" always
 * looks like "no data" and never like a broken screen.
 */
export default function UnavailableNotice({ reason }: { reason?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-amber-900/15 bg-amber-50 px-4 py-4">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <div>
        <p className="text-sm font-bold text-amber-900">Not enough data yet</p>
        {reason && <p className="mt-1 text-sm leading-relaxed text-amber-800/80">{reason}</p>}
      </div>
    </div>
  );
}
