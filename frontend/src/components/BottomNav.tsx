'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { Home, LayoutDashboard, LineChart, FlaskConical, PiggyBank, Terminal as TerminalIcon, Wallet, Wrench } from 'lucide-react';
import { isFarmRoute } from '@/lib/surfaces';
import { useLanguage } from '@/context/LanguageContext';

const ANALYST_ITEMS = [
  { href: '/trader', label: 'Desk', icon: LayoutDashboard },
  { href: '/market-explorer', label: 'Markets', icon: LineChart },
  { href: '/intelligence-lab', label: 'Lab', icon: FlaskConical },
  { href: '/trader-tools', label: 'Tools', icon: Wrench },
  { href: '/terminal', label: 'Terminal', icon: TerminalIcon },
];

// The farm surface has no use for Lab/Terminal/Markets (those are
// analyst-only, trader-facing views) and gains two destinations the
// analyst nav has no equivalent of: the one-answer sell plan and the
// personal savings ledger it feeds. These are the app's primary users, so
// their two headline features sit in the bar itself rather than one tap
// deeper inside "Tools".
const FARM_ITEMS = [
  { href: '/', labelKey: 'nav.home', icon: Home },
  { href: '/prices', labelKey: 'nav.prices', icon: LineChart },
  { href: '/sell-plan', labelKey: 'nav.sell_plan', icon: Wallet },
  { href: '/my-money', labelKey: 'nav.my_money', icon: PiggyBank },
  { href: '/tools', labelKey: 'nav.tools', icon: Wrench },
] as const;

/**
 * Mobile-first bottom navigation. Replaces the old placeholder that
 * rendered three empty grey squares instead of real destinations.
 * Hidden on md+ where the top nav already covers wayfinding, and hidden
 * on /terminal, which is a full-bleed command surface of its own.
 */
export default function BottomNav() {
  const pathname = usePathname();
  const { t } = useLanguage();

  if (pathname === '/terminal') return null;

  // On the farmer surface the bar has to stay legible in sunlight against
  // a bright page, so it becomes solid paper with the leaf accent rather
  // than the dark glass used on the analyst views.
  const farm = isFarmRoute(pathname);
  const activeColour = farm ? 'var(--leaf)' : 'var(--accent-strong)';
  const idleColour = farm ? 'var(--farm-ink-faint)' : 'var(--neutral-signal)';
  const ITEMS = farm ? FARM_ITEMS : ANALYST_ITEMS;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:hidden"
      aria-label="Primary"
    >
      <div
        className={
          farm
            ? 'flex w-full max-w-sm items-center justify-around rounded-2xl border border-[var(--farm-line)] bg-white px-2 py-2 shadow-[0_16px_36px_-18px_rgba(42,33,25,0.45)]'
            : 'glass-panel flex w-full max-w-sm items-center justify-around rounded-2xl px-2 py-2 shadow-[0_18px_40px_-16px_rgba(0,0,0,0.45)]'
        }
      >
        {ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative flex flex-1 flex-col items-center gap-1 rounded-xl px-3 py-1.5"
            >
              {active && (
                <motion.span
                  layoutId="bottom-nav-active"
                  className="absolute inset-0 rounded-xl"
                  style={{ background: farm ? 'var(--leaf-wash)' : 'var(--accent-soft)' }}
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                />
              )}
              <Icon
                className="relative z-10 h-5 w-5 transition-colors"
                strokeWidth={active ? 2.4 : 1.8}
                style={{ color: active ? activeColour : idleColour }}
              />
              <span
                className={
                  farm
                    ? 'relative z-10 text-[11px] font-bold transition-colors'
                    : 'relative z-10 text-[9.5px] font-bold uppercase tracking-wider transition-colors'
                }
                style={{ color: active ? activeColour : idleColour }}
              >
                {'labelKey' in item ? t(item.labelKey) : item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
