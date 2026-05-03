import React from 'react';

interface DecisionBadgeProps {
  decision: 'SELL' | 'HOLD' | 'WAIT';
}

const DecisionBadge: React.FC<DecisionBadgeProps> = ({ decision }) => {
  const styles = {
    SELL: 'bg-red-500/10 text-red-600 border-red-500/20',
    HOLD: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
    WAIT: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  };

  return (
    <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-tighter border ${styles[decision]}`}>
      {decision}
    </span>
  );
};

export default DecisionBadge;
