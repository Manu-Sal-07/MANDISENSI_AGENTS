'use client';

/**
 * Plan My Harvest Sale.
 *
 * The single highest-value screen on the farmer surface: one answer that
 * combines three already-shipped features (My Harvest in Rupees, Hold-or-Rot,
 * Where to Sell) into where, when and for how much, instead of asking a
 * farmer to open three tools and do the comparison in their head.
 *
 * Every rupee figure here is one the backend already computed for a single
 * tool; this page adds no new arithmetic beyond picking the largest of the
 * three totals it already trusts.
 */

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Check, Loader2, MapPin, PiggyBank, Sparkles } from 'lucide-react';

import UnavailableNotice from '@/components/farm/tools/UnavailableNotice';
import { CropPicker, MandiPicker, QuantityPicker } from '@/components/farm/tools/ContextPicker';
import { ToolProvider, useToolSelection } from '@/context/ToolContext';
import { useLanguage } from '@/context/LanguageContext';
import { farmerApi, type HarvestPlan, type HoldOrRotResult, type WhereToSellResult } from '@/services/farmerApi';
import { savePlan, type PlanChoice } from '@/lib/myMoney';
import { formatDate, formatRupees } from '@/lib/format';
import { resolveProduce } from '@/components/farm/ProduceIcon';

interface Option {
  choice: PlanChoice;
  title: string;
  subtitle: string;
  total: number;
  targetDate: string;
  targetMandiId: string;
  targetMandiName: string;
}

function SellPlanBody() {
  const { commodity, mandiId, quantityQuintals } = useToolSelection();
  const { t } = useLanguage();
  const [saved, setSaved] = useState(false);
  const produce = resolveProduce(commodity);

  const harvest = useQuery<HarvestPlan>({
    queryKey: ['sellplan-harvest', commodity, mandiId, quantityQuintals],
    queryFn: () => farmerApi.harvestPlan(commodity, mandiId, quantityQuintals),
  });
  const hold = useQuery<HoldOrRotResult>({
    queryKey: ['sellplan-hold', commodity, mandiId, quantityQuintals],
    queryFn: () => farmerApi.holdOrSell(commodity, mandiId, quantityQuintals),
  });
  const travel = useQuery<WhereToSellResult>({
    queryKey: ['sellplan-travel', commodity, mandiId, quantityQuintals],
    queryFn: () => farmerApi.whereToSell(commodity, { mandiId }, quantityQuintals),
  });

  const isLoading = harvest.isFetching || hold.isFetching || travel.isFetching;

  const { options, winner, mandiName, unavailable } = useMemo(() => {
    const mandiRow = travel.data?.mandis?.find((m) => m.mandi_id === mandiId);
    const localMandiName = mandiRow?.mandi_name ?? mandiId;

    if (hold.data?.status !== 'OK' || !hold.data.sell_today_value) {
      return { options: [] as Option[], winner: null as Option | null, mandiName: localMandiName, unavailable: true };
    }

    const opts: Option[] = [
      {
        choice: 'sell_today',
        title: t('sellplan.option_sell_today'),
        subtitle: localMandiName,
        total: hold.data.sell_today_value,
        targetDate: new Date().toISOString().slice(0, 10),
        targetMandiId: mandiId,
        targetMandiName: localMandiName,
      },
    ];

    if (hold.data.best_option && hold.data.best_option.net_value > hold.data.sell_today_value) {
      opts.push({
        choice: 'wait',
        title: t('sellplan.option_wait'),
        subtitle: localMandiName,
        total: hold.data.best_option.net_value,
        targetDate: hold.data.best_option.target_date || new Date().toISOString().slice(0, 10),
        targetMandiId: mandiId,
        targetMandiName: localMandiName,
      });
    }

    if (travel.data?.status === 'OK' && travel.data.best_mandi_id && travel.data.best_mandi_id !== mandiId) {
      const bestRow = travel.data.mandis?.find((m) => m.mandi_id === travel.data!.best_mandi_id);
      if (bestRow && bestRow.net_total > hold.data.sell_today_value) {
        opts.push({
          choice: 'travel',
          title: t('sellplan.option_travel'),
          subtitle: bestRow.mandi_name,
          total: bestRow.net_total,
          targetDate: new Date().toISOString().slice(0, 10),
          targetMandiId: bestRow.mandi_id,
          targetMandiName: bestRow.mandi_name,
        });
      }
    }

    const best = opts.reduce((a, b) => (b.total > a.total ? b : a), opts[0]);
    return { options: opts, winner: best, mandiName: localMandiName, unavailable: false };
  }, [hold.data, travel.data, mandiId, t]);

  const handleFollow = () => {
    if (!winner || !hold.data?.sell_today_value) return;
    savePlan({
      commodity,
      mandiId,
      mandiName,
      quantityQuintals,
      choice: winner.choice,
      planTotal: winner.total,
      baselineTotal: hold.data.sell_today_value,
      targetDate: winner.targetDate,
      targetMandiId: winner.targetMandiId,
      targetMandiName: winner.targetMandiName,
    });
    setSaved(true);
  };

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-2xl px-4 pb-10 pt-6 lg:max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <h1 className="farm-display text-2xl text-[var(--farm-ink)] sm:text-3xl">{t('sellplan.title')}</h1>
          <p className="mt-1 text-sm text-[var(--farm-ink-faint)]">{t('sellplan.subtitle')}</p>
        </motion.div>

        <div className="farm-card mt-5 space-y-4 p-4">
          <CropPicker />
          <div className="grid grid-cols-2 gap-3">
            <MandiPicker />
            <QuantityPicker />
          </div>
        </div>

        {isLoading && (
          <div className="mt-8 flex items-center justify-center gap-2 py-10 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Working out {produce.label.toLowerCase()}&rsquo;s best plan…
          </div>
        )}

        {!isLoading && unavailable && (
          <div className="mt-6">
            <UnavailableNotice reason={hold.data?.reason} />
          </div>
        )}

        {!isLoading && !unavailable && winner && (
          <>
            {/* ── The one answer ──────────────────────────────────── */}
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="farm-card farm-card-lift relative mt-6 overflow-hidden"
            >
              <div className="h-2.5 w-full" style={{ background: 'var(--leaf)' }} />
              <div className="p-6">
                <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[var(--leaf)]">
                  <Sparkles className="h-3.5 w-3.5" /> {t('sellplan.best_plan')}
                </p>
                <h2 className="farm-display mt-2 text-3xl leading-tight text-[var(--farm-ink)] sm:text-4xl">
                  {winner.title}
                </h2>
                <p className="mt-1.5 flex items-center gap-1.5 text-base font-semibold text-[var(--farm-ink-soft)]">
                  <MapPin className="h-4 w-4 shrink-0" />
                  {winner.subtitle}
                  {winner.choice !== 'sell_today' && (
                    <span className="text-[var(--farm-ink-faint)]"> · {formatDate(winner.targetDate)}</span>
                  )}
                </p>
                <p className="farm-display mt-4 text-4xl text-[var(--leaf-deep)] sm:text-5xl">
                  {formatRupees(winner.total)}
                </p>
                {winner.total > (hold.data?.sell_today_value ?? 0) && winner.choice !== 'sell_today' && (
                  <p className="mt-1 text-sm font-semibold text-[var(--leaf-deep)]">
                    +{formatRupees(winner.total - (hold.data?.sell_today_value ?? 0))}{' '}
                    {t('sellplan.vs_selling_today')}
                  </p>
                )}
                {winner.choice === 'wait' && (
                  <p className="mt-3 text-xs leading-relaxed text-[var(--farm-ink-faint)]">
                    {t('sellplan.spoilage_note')}
                  </p>
                )}

                <button
                  type="button"
                  onClick={handleFollow}
                  disabled={saved}
                  className="farm-focus mt-5 flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-base font-bold text-white transition-transform active:scale-[0.99] disabled:opacity-70"
                  style={{ background: saved ? 'var(--farm-line-strong)' : 'var(--leaf)' }}
                >
                  {saved ? <Check className="h-4 w-4" /> : <PiggyBank className="h-4 w-4" />}
                  {saved ? t('sellplan.saved_to_my_money') : t('sellplan.follow_this')}
                </button>
              </div>
            </motion.div>

            {/* ── Every option, compared ──────────────────────────── */}
            <div className="mt-5 space-y-2.5">
              {options.map((opt, i) => (
                <motion.div
                  key={opt.choice}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                  className="farm-row flex items-center justify-between p-3.5"
                  style={
                    opt.choice === winner.choice
                      ? { borderColor: 'var(--leaf)', background: 'var(--leaf-wash)' }
                      : undefined
                  }
                >
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-[var(--farm-ink)]">{opt.title}</p>
                    <p className="mt-0.5 truncate text-xs text-[var(--farm-ink-faint)]">
                      {opt.subtitle}
                      {opt.choice !== 'sell_today' && ` · ${formatDate(opt.targetDate)}`}
                    </p>
                  </div>
                  <span className="farm-display shrink-0 text-lg text-[var(--farm-ink)]">
                    {formatRupees(opt.total)}
                  </span>
                </motion.div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default function SellPlanPage() {
  return (
    <ToolProvider>
      <SellPlanBody />
    </ToolProvider>
  );
}
