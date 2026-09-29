'use client';

import { useState } from 'react';
import { Activity, Bell, Search, Sun, Moon, Menu, X, Sparkles } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import FarmHeader from '@/components/farm/FarmHeader';
import { isFarmRoute } from '@/lib/surfaces';

const NAV_LINKS = [
  { href: '/market-explorer', label: 'Market Explorer' },
  { href: '/intelligence-lab', label: 'Intelligence Lab' },
  { href: '/terminal', label: 'Command Center' },
  { href: '/ai-brief', label: 'AI Brief' },
];

export default function TopBar() {
  const { theme, toggleTheme, mounted } = useTheme();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // /terminal is a self-contained, full-bleed command surface with its own
  // header — this bar would fight for vertical space there.
  if (pathname === '/terminal') return null;

  // The farmer surface has its own header: no product nav, no theme
  // switch, and the mandi location promoted to the one thing at the top.
  if (isFarmRoute(pathname)) return <FarmHeader />;

  return (
    <header className="glass-panel sticky top-0 z-50 w-full">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        {/* Brand */}
        <Link href="/" className="group flex shrink-0 items-center gap-2.5">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--intelligence)] shadow-[0_6px_18px_-6px_var(--accent-glow)] transition-transform group-hover:scale-105">
            <Activity className="h-4.5 w-4.5 text-white" strokeWidth={2.4} />
            <span className="live-dot absolute -right-0.5 -top-0.5" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-display text-base font-bold tracking-tight text-foreground">
              MandiSense <span className="gradient-text-brand">AI</span>
            </span>
            <span className="label-caps mt-0.5 text-[8.5px]">Market Intelligence</span>
          </div>
        </Link>

        {/* Primary nav */}
        <nav className="hidden lg:flex items-center gap-1">
          {NAV_LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className="relative rounded-lg px-3.5 py-2 text-sm font-semibold transition-colors"
                style={{ color: active ? 'var(--foreground)' : 'var(--neutral-signal)' }}
              >
                {active && (
                  <motion.span
                    layoutId="topbar-active-pill"
                    className="absolute inset-0 rounded-lg bg-surface-3"
                    transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                  />
                )}
                <span className="relative z-10">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Search */}
        <div className="hidden md:flex flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-signal" />
            <input
              type="text"
              placeholder="Search mandi or commodity…"
              disabled
              className="w-full cursor-not-allowed rounded-full border border-border bg-surface-2 py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-neutral-signal focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-60"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground active:scale-95"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {!mounted ? (
              <div className="h-4.5 w-4.5" />
            ) : theme === 'dark' ? (
              <Sun className="h-4.5 w-4.5" />
            ) : (
              <Moon className="h-4.5 w-4.5" />
            )}
          </button>

          <button className="relative hidden h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground sm:flex">
            <Bell className="h-4.5 w-4.5" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-bearish ring-2 ring-[var(--surface-0)]" />
          </button>

          <Link
            href="/for-evaluators"
            className="btn-primary hidden text-xs !px-3 !py-1.5 sm:inline-flex"
          >
            <Sparkles className="h-3.5 w-3.5" />
            For Evaluators
          </Link>

          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-neutral-signal transition-colors hover:bg-surface-2 hover:text-foreground lg:hidden"
            aria-label="Toggle menu"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden border-t border-border lg:hidden"
          >
            <div className="flex flex-col gap-1 px-4 py-3">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="rounded-lg px-3 py-2.5 text-sm font-semibold text-foreground hover:bg-surface-2"
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
