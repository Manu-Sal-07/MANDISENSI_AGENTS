'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { Activity, Bot, FlaskConical, LayoutDashboard, LineChart, Menu, Moon, Sparkles, Sprout, Sun, Terminal, Wrench, X } from 'lucide-react';

import { useTheme } from '@/context/ThemeContext';

const LINKS = [
  { href: '/trader', label: 'Desk', icon: LayoutDashboard },
  { href: '/market-explorer', label: 'Explorer', icon: LineChart },
  { href: '/intelligence-lab', label: 'Lab', icon: FlaskConical },
  { href: '/terminal', label: 'Command Center', icon: Terminal },
  { href: '/trader-tools', label: 'Tools', icon: Wrench },
  { href: '/ai-brief', label: 'AI Brief', icon: Bot },
];

/**
 * Header for the trading desk and the other analyst pages: brand, one row of
 * destinations with an animated active marker, a live indicator, a way across to
 * the farmer app, and the theme switch. No decorative controls.
 */
export default function TraderHeader() {
  const pathname = usePathname();
  const { theme, toggleTheme, mounted } = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <header className="tb-header sticky top-0 z-50 w-full">
      <div className="mx-auto flex h-16 max-w-[1480px] items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/trader" className="group flex shrink-0 items-center gap-2.5">
          <span className="tb-logo relative flex h-9 w-9 items-center justify-center rounded-xl">
            <Activity className="h-[18px] w-[18px] text-white" strokeWidth={2.4} />
            <span className="live-dot absolute -right-0.5 -top-0.5" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-base font-bold tracking-tight text-foreground">
              MandiSense <span className="tb-gradient-text">AI</span>
            </span>
            <span className="mt-1 text-[9px] font-bold uppercase tracking-[0.28em] text-neutral-signal">Trading Desk</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Trading desk">
          {LINKS.map((l) => {
            const active = l.href === '/trader' ? pathname === '/trader' : pathname.startsWith(l.href);
            const Icon = l.icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                className="relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition-colors"
                style={{ color: active ? 'var(--foreground)' : 'var(--neutral-signal)' }}
              >
                {active && (
                  <motion.span
                    layoutId="desk-nav-active"
                    className="tb-navpill absolute inset-0 rounded-xl"
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  />
                )}
                <Icon className="relative z-10 h-4 w-4" />
                <span className="relative z-10">{l.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <span className="tb-live hidden items-center gap-2 rounded-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] xl:flex">
            <span className="live-dot" /> Live desk
          </span>
          <Link
            href="/"
            className="tb-farmer hidden items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold sm:flex"
            title="Open the farmer app"
          >
            <Sprout className="h-4 w-4" /> Farmer app
          </Link>
          <Link
            href="/for-evaluators"
            aria-label="For evaluators"
            title="For evaluators"
            className="hidden h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground md:flex"
          >
            <Sparkles className="h-[18px] w-[18px]" />
          </Link>
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground active:scale-95"
          >
            {!mounted ? <span className="h-4 w-4" /> : theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
          </button>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
            className="flex h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground lg:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden border-t border-border lg:hidden"
          >
            <div className="grid grid-cols-2 gap-2 p-3">
              {[...LINKS, { href: '/', label: 'Farmer app', icon: Sprout }].map((l) => {
                const Icon = l.icon;
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2.5 rounded-xl border border-border bg-surface-1 px-3.5 py-3 text-sm font-semibold text-foreground"
                  >
                    <Icon className="h-4 w-4 text-[var(--tb-cyan)]" /> {l.label}
                  </Link>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
