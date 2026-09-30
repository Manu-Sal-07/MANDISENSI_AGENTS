'use client';

/**
 * My Money.
 *
 * The ledger that closes the loop on "Plan My Harvest Sale": for every
 * plan a farmer said they would follow, this checks whether the mandi
 * actually printed the price the plan expected, once its target date has
 * passed. It never asks the farmer to self-report an outcome, and it
 * never trusts the plan's own forecast to grade itself -- the verdict
 * comes from `farmerApi.priceOnDate`, a real recorded print, the same
 * honesty rule the rest of the farmer surface follows.
 *
 * Storage is on-device only (see `lib/myMoney.ts`); the disclaimer at the
 * foot of the page says so rather than implying otherwise.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Loader2, PiggyBank, Sparkles, Trash2 } from 'lucide-react';

import ProduceIcon, { resolveProduce } from '@/components/farm/ProduceIcon';
import { useLanguage } from '@/context/LanguageContext';
import { farmerApi } from '@/services/farmerApi';
import { clearAll, isTargetDateReached, listPlans, type SavedPlan } from '@/lib/myMoney';
import { formatDate, formatRupees } from '@/lib/format';

function PlanRow({ plan }: { plan: SavedPlan }) {
  const { t } = useLanguage();
  const produce = resolveProduce(plan.commodity);
  const reached = isTargetDateReached(plan);
  const needsCheck = reached && plan.choice !== 'sell_today';

  const check = useQuery({
    queryKey: ['my-money-check', plan.id],
    queryFn: () => farmerApi.priceOnDate(plan.commodity, plan.targetMandiId, plan.targetDate),
    enabled: needsCheck,
    staleTime: 1000 * 60 * 60,
  });

  let gain: number | null = null;
  let verified: number | null = null;
  if (plan.choice === 'sell_today') {
    gain = plan.planTotal - plan.baselineTotal;
    verified = plan.planTotal;
  } else if (check.data?.status === 'OK' && check.data.modal_price != null) {
    verified = check.data.modal_price * plan.quantityQuintals;
    gain = verified - plan.baselineTotal;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="farm-row p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <ProduceIcon name={plan.commodity} size="md" />
          <div className="min-w-0">
            <p className="text-sm font-bold text-[var(--farm-ink)]">
              {produce.label} · {plan.mandiName}
            </p>
            <p className="mt-0.5 text-xs text-[var(--farm-ink-faint)]">
              {plan.quantityQuintals} qtl · {formatDate(plan.createdAt)}
              {plan.choice !== 'sell_today' && ` → ${plan.targetMandiName} · ${formatDate(plan.targetDate)}`}
            </p>
          </div>
        </div>

        <div className="shrink-0 text-right">
          {!reached ? (
            <p className="text-xs font-semibold text-[var(--call-wait)]">{t('mymoney.pending')}</p>
          ) : needsCheck && check.isFetching ? (
            <span className="flex items-center gap-1 text-xs text-[var(--farm-ink-faint)]">
              <Loader2 className="h-3 w-3 animate-spin" /> {t('mymoney.checking')}
            </span>
          ) : needsCheck && check.data?.status !== 'OK' ? (
            <p className="max-w-[8rem] text-xs text-[var(--farm-ink-faint)]">{t('mymoney.not_verifiable')}</p>
          ) : gain != null ? (
            <>
              <p
                className="farm-display text-xl"
                style={{ color: gain >= 0 ? 'var(--leaf-deep)' : 'var(--call-sell)' }}
              >
                {gain >= 0 ? '+' : ''}
                {formatRupees(gain)}
              </p>
              <p className="text-[11px] text-[var(--farm-ink-faint)]">{formatRupees(verified)} actual</p>
            </>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}

export default function MyMoneyPage() {
  const { t } = useLanguage();
  const [plans, setPlans] = useState<SavedPlan[]>([]);

  useEffect(() => {
    setPlans(listPlans());
  }, []);

  const totalRealised = useMemo(
    () =>
      plans
        .filter((p) => p.choice === 'sell_today')
        .reduce((sum, p) => sum + (p.planTotal - p.baselineTotal), 0),
    [plans]
  );

  const handleClear = () => {
    clearAll();
    setPlans([]);
  };

  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-2xl px-4 pb-10 pt-6 lg:max-w-3xl">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <h1 className="farm-display flex items-center gap-2 text-2xl text-[var(--farm-ink)] sm:text-3xl">
            <PiggyBank className="h-6 w-6 shrink-0" style={{ color: 'var(--leaf)' }} />
            {t('mymoney.title')}
          </h1>
          <p className="mt-1 text-sm text-[var(--farm-ink-faint)]">{t('mymoney.subtitle')}</p>
        </motion.div>

        {plans.length === 0 ? (
          <div className="farm-card mt-6 p-6 text-center">
            <Sparkles className="mx-auto h-6 w-6 text-[var(--farm-ink-faint)]" />
            <p className="mt-2 text-base font-semibold text-[var(--farm-ink)]">{t('mymoney.empty_title')}</p>
            <p className="mt-1 text-sm text-[var(--farm-ink-soft)]">{t('mymoney.empty_body')}</p>
          </div>
        ) : (
          <>
            {totalRealised !== 0 && (
              <div className="farm-card mt-5 p-5">
                <p className="text-xs font-semibold text-[var(--farm-ink-faint)]">{t('mymoney.total_saved')}</p>
                <p
                  className="farm-display mt-1 text-3xl"
                  style={{ color: totalRealised >= 0 ? 'var(--leaf-deep)' : 'var(--call-sell)' }}
                >
                  {totalRealised >= 0 ? '+' : ''}
                  {formatRupees(totalRealised)}
                </p>
              </div>
            )}

            <div className="mt-5 space-y-2.5">
              {plans.map((plan) => (
                <PlanRow key={plan.id} plan={plan} />
              ))}
            </div>

            <button
              type="button"
              onClick={handleClear}
              className="farm-focus mt-6 flex items-center gap-1.5 text-xs font-semibold text-[var(--farm-ink-faint)] hover:text-[var(--call-sell)]"
            >
              <Trash2 className="h-3.5 w-3.5" /> {t('mymoney.clear_all')}
            </button>
          </>
        )}

        <p className="mt-8 text-center text-xs leading-relaxed text-[var(--farm-ink-faint)]">
          {t('mymoney.disclaimer')}
        </p>
      </main>
    </div>
  );
}
