'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, LayoutGrid } from 'lucide-react';

import DeskHero from '@/components/trader/DeskHero';
import { CommodityPicker, MandiPicker } from '@/components/trader/shared';
import { TRADER_TOOLS, toolBySlug } from '@/lib/traderTools';
import { farmerApi } from '@/services/farmerApi';
import { useDeskFocus } from '@/store/deskFocus';

/** Mandis the tools can be focused on; shared by every tool page. */
export function useDeskMandis() {
  const { data } = useQuery({
    queryKey: ['trader-mandis'],
    queryFn: () => farmerApi.listMandis(),
    staleTime: Infinity,
  });
  return data?.mandis ?? [{ mandi_id: 'kolar_apmc', mandi_name: 'Kolar' }];
}

/**
 * The page frame every trader tool shares: banner with a breadcrumb back to the
 * tools hub, the commodity / mandi focus for tools that use it, the tool itself
 * at a comfortable reading width, and previous / next navigation.
 */
export default function ToolShell({ slug, children }: { slug: string; children: (focus: { commodity: string; mandiId: string }) => React.ReactNode }) {
  const tool = toolBySlug(slug)!;
  const { commodity, mandiId, setCommodity, setMandiId } = useDeskFocus();
  const mandis = useDeskMandis();
  const i = TRADER_TOOLS.findIndex((t) => t.slug === slug);
  const prev = TRADER_TOOLS[(i - 1 + TRADER_TOOLS.length) % TRADER_TOOLS.length];
  const next = TRADER_TOOLS[(i + 1) % TRADER_TOOLS.length];
  const Icon = tool.icon;

  return (
    <div className="tb-clear min-h-screen pb-28 md:pb-20">
      <div className="mx-auto max-w-[1100px] px-4 pt-8 sm:px-6">
        <DeskHero
          parent={{ label: 'Tools', href: '/trader-tools' }}
          kicker={tool.title}
          title={tool.title}
          subtitle={tool.blurb}
          icon={<Icon className="h-7 w-7" />}
          accent={tool.accent}
          photo={tool.photo}
        >
          {tool.focus && (
            <div className="tb-panel flex flex-wrap items-center gap-2 rounded-2xl px-3 py-3">
              <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-signal">Focus</span>
              <CommodityPicker value={commodity} onChange={setCommodity} />
              <MandiPicker value={mandiId} onChange={setMandiId} mandis={mandis} />
            </div>
          )}
        </DeskHero>

        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.5 }} className="tb-tool mt-6">
          {children({ commodity, mandiId })}
        </motion.div>

        {/* previous / next */}
        <nav aria-label="Other tools" className="mt-10 grid gap-3 sm:grid-cols-[1fr_auto_1fr]">
          <Link href={prev.href} className="tb-panel tb-navcard farm-focus group flex items-center gap-3 rounded-2xl px-4 py-3.5">
            <ArrowLeft className="h-5 w-5 shrink-0 text-neutral-signal transition-transform group-hover:-translate-x-1" />
            <span className="min-w-0">
              <span className="block text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-signal">Previous</span>
              <span className="block truncate text-sm font-bold text-foreground">{prev.title}</span>
            </span>
          </Link>
          <Link href="/trader-tools" className="tb-panel tb-navcard farm-focus flex items-center justify-center gap-2 rounded-2xl px-5 py-3.5 text-sm font-bold text-foreground">
            <LayoutGrid className="h-4 w-4" /> All tools
          </Link>
          <Link href={next.href} className="tb-panel tb-navcard farm-focus group flex items-center justify-end gap-3 rounded-2xl px-4 py-3.5 text-right">
            <span className="min-w-0">
              <span className="block text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-signal">Next</span>
              <span className="block truncate text-sm font-bold text-foreground">{next.title}</span>
            </span>
            <ArrowRight className="h-5 w-5 shrink-0 text-neutral-signal transition-transform group-hover:translate-x-1" />
          </Link>
        </nav>
      </div>
    </div>
  );
}
