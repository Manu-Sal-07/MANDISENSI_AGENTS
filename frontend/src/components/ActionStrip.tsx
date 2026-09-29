'use client';

import { useState } from 'react';
import { Bell, Filter, Map, Zap } from 'lucide-react';

const ACTIONS = [
  { id: 'nearby', label: 'Nearby', icon: Zap },
  { id: 'select_mandi', label: 'Select Mandi', icon: Map },
  { id: 'all_crops', label: 'All Crops', icon: Filter },
  { id: 'alerts', label: 'Alerts', icon: Bell },
];

export default function ActionStrip() {
  const [active, setActive] = useState('nearby');

  return (
    <div className="w-full border-b border-border bg-surface-0 pb-3">
      <div className="no-scrollbar flex gap-2.5 overflow-x-auto px-4">
        {ACTIONS.map((action) => {
          const Icon = action.icon;
          const isActive = active === action.id;
          return (
            <button
              key={action.id}
              onClick={() => setActive(action.id)}
              className={isActive ? 'chip chip-active whitespace-nowrap' : 'chip whitespace-nowrap'}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="uppercase tracking-wider">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
