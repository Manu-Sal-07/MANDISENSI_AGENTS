'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { farmerApi } from '@/services/farmerApi';
import { CommodityPicker, MandiPicker } from '@/components/trader/shared';
import SpreadScanner from '@/components/trader/SpreadScanner';
import VolatilityPanel from '@/components/trader/VolatilityPanel';
import AnalogsPanel from '@/components/trader/AnalogsPanel';
import ScenariosPanel from '@/components/trader/ScenariosPanel';
import ForwardPriceCalculator from '@/components/trader/ForwardPriceCalculator';
import PositionBook from '@/components/trader/PositionBook';

/**
 * Trader Tools.
 *
 * The frontend surface for `mandisense_ai/trader/` — six analytics built to
 * replace fabricated panels found across Market Explorer, the Intelligence
 * Lab and the Command Center (hardcoded exposure volumes, hand-written
 * counterfactual formulas, permanently-empty analog and regime panels; see
 * the trader-side audit). Every number on this page is computed from the
 * real observation archive or a real recorded position — nothing here is
 * a placeholder waiting on a data source that hasn't arrived yet.
 *
 * A shared commodity + mandi selector drives every panel below it except
 * the spread scanner (which compares *across* mandis for one commodity, so
 * a single mandi selection would not apply) and the position book (which
 * has its own selector, since a book holds many positions across many
 * series at once).
 */
export default function TraderToolsPage() {
  const [commodity, setCommodity] = useState('tomato');
  const [mandiId, setMandiId] = useState('kolar_apmc');

  const { data: mandiData } = useQuery({
    queryKey: ['trader-mandis'],
    queryFn: () => farmerApi.listMandis(),
    staleTime: Infinity,
  });
  const mandis = mandiData?.mandis ?? [{ mandi_id: 'kolar_apmc', mandi_name: 'Kolar' }];

  return (
    <div className="surface-root min-h-screen pb-16">
      <div className="mx-auto max-w-7xl px-4 pt-8 sm:px-6">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--intelligence)]">
              <Sparkles className="h-4.5 w-4.5 text-white" />
            </span>
            <div>
              <h1 className="font-display text-xl font-black tracking-tight text-foreground">Trader Tools</h1>
              <p className="text-xs text-neutral-signal">
                Spreads, volatility, precedent, scenarios, forward pricing and real position risk
              </p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface-1 px-3 py-2.5">
            <span className="text-xs font-semibold text-neutral-signal">Focus:</span>
            <CommodityPicker value={commodity} onChange={setCommodity} />
            <MandiPicker value={mandiId} onChange={setMandiId} mandis={mandis} />
          </div>
        </motion.div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <SpreadScanner />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <VolatilityPanel commodity={commodity} mandiId={mandiId} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <AnalogsPanel commodity={commodity} mandiId={mandiId} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <ScenariosPanel commodity={commodity} mandiId={mandiId} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <ForwardPriceCalculator commodity={commodity} mandiId={mandiId} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <PositionBook mandis={mandis} />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
