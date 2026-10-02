import type { FarmCall } from '@/services/farmerApi';
import type { Lang } from '@/lib/i18n/translations';
import { say } from '@/lib/i18n/farmCopy';

/**
 * How a call looks and reads. One place, so the hero, the crop rail and the
 * sale planner can never disagree about what "Hold" is coloured or called.
 *
 * A crop with no earned call gets the neutral ink tone on purpose: drawing a
 * range in a decision colour would imply advice the record has not earned.
 */
export interface Tone {
  key: 'sell' | 'hold' | 'wait' | 'range';
  colour: string;
  wash: string;
  label: string;
}

export function toneOf(call: FarmCall, lang: Lang): Tone {
  if (call.type === 'ADVISED' && call.decision === 'SELL')
    return { key: 'sell', colour: 'var(--call-sell)', wash: 'var(--call-sell-wash)', label: say('call.sell', lang) };
  if (call.type === 'ADVISED' && call.decision === 'HOLD')
    return { key: 'hold', colour: 'var(--call-hold)', wash: 'var(--call-hold-wash)', label: say('call.hold', lang) };
  if (call.type === 'ABSTAINED')
    return { key: 'wait', colour: 'var(--call-wait)', wash: 'var(--call-wait-wash)', label: say('call.wait', lang) };
  return { key: 'range', colour: 'var(--farm-ink-soft)', wash: 'rgba(42,33,25,0.05)', label: say('call.range', lang) };
}
