import React from 'react';

interface DecisionBadgeProps {
  decision: 'SELL' | 'HOLD' | 'WAIT';
}

const STYLES: Record<string, React.CSSProperties> = {
  SELL: { color: 'var(--bearish)', background: 'var(--bearish-glow)', borderColor: 'color-mix(in oklch, var(--bearish) 35%, transparent)' },
  HOLD: { color: 'var(--bullish)', background: 'var(--bullish-glow)', borderColor: 'color-mix(in oklch, var(--bullish) 35%, transparent)' },
  WAIT: { color: 'var(--warning)', background: 'var(--warning-glow)', borderColor: 'color-mix(in oklch, var(--warning) 35%, transparent)' },
};

const DecisionBadge: React.FC<DecisionBadgeProps> = ({ decision }) => {
  return (
    <span
      className="rounded-lg border px-2.5 py-1 text-[10px] font-black uppercase tracking-wider"
      style={STYLES[decision]}
    >
      {decision}
    </span>
  );
};

export default DecisionBadge;
