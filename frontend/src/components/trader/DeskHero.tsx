'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

/**
 * The banner every trader page opens with, so the desk reads as one product:
 * breadcrumb back to the desk, a kicker chip in the page's accent colour, the
 * title and purpose, and a slot on the right for the page's own controls.
 */
export default function DeskHero({
  parent,
  kicker,
  title,
  subtitle,
  icon,
  accent = 'cyan',
  photo,
  children,
  className = '',
}: {
  parent?: { label: string; href: string };
  kicker: string;
  title: string;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  accent?: 'cyan' | 'violet' | 'amber' | 'green';
  photo?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={`tb-hero tb-accent-${accent} relative overflow-hidden rounded-3xl px-5 py-6 sm:px-8 sm:py-8 ${className}`}
    >
      {photo && <div className="tb-hero-photo" style={{ backgroundImage: `url(/photos/${photo}.jpg)` }} aria-hidden="true" />}
      <div className="tb-hero-glow" aria-hidden="true" />
      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-signal">
            <Link href="/trader" className="transition-colors hover:text-foreground">Desk</Link>
            <ChevronRight className="h-3 w-3" />
            {parent && (
              <>
                <Link href={parent.href} className="transition-colors hover:text-foreground">{parent.label}</Link>
                <ChevronRight className="h-3 w-3" />
              </>
            )}
            <span className="tb-accent-text">{kicker}</span>
          </nav>
          <div className="flex items-center gap-4">
            {icon && <span className="tb-hero-icon flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl">{icon}</span>}
            <div className="min-w-0">
              <h1 className="font-display text-3xl font-black leading-tight tracking-tight text-foreground sm:text-4xl">{title}</h1>
              {subtitle && <div className="mt-1.5 max-w-[68ch] text-sm leading-relaxed text-neutral-signal sm:text-[15px]">{subtitle}</div>}
            </div>
          </div>
        </div>
        {children && <div className="min-w-0 lg:max-w-[46%]">{children}</div>}
      </div>
    </motion.header>
  );
}
