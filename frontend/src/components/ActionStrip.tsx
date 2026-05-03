import { Bell, Filter, Map, Zap } from 'lucide-react';

const ACTIONS = [
  { id: 'nearby', label: 'Nearby', icon: Zap, active: true },
  { id: 'select_mandi', label: 'Select Mandi', icon: Map },
  { id: 'all_crops', label: 'All Crops', icon: Filter },
  { id: 'alerts', label: 'Alerts', icon: Bell },
];

export default function ActionStrip() {
  return (
    <div className="w-full bg-white dark:bg-black border-b border-zinc-100 dark:border-zinc-900 pb-3">
      <div className="flex gap-2.5 overflow-x-auto px-4 no-scrollbar scroll-smooth">
        {ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              className={`flex-none flex items-center gap-2 px-4 py-2 rounded-full border transition-all active:scale-95 whitespace-nowrap ${
                action.active
                  ? 'bg-zinc-900 dark:bg-white text-white dark:text-black border-zinc-900 dark:border-white shadow-md font-semibold'
                  : 'bg-white dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="text-xs uppercase tracking-wider">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
