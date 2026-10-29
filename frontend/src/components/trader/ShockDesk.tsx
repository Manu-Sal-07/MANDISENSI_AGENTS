'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Waves } from 'lucide-react';
import { ToolCard, LoadingRow, RefusalNotice, formatPct } from './shared';
import { shockApi, type CrossLink, type ShockItem, type StudyRow, type Tier } from '@/services/shockApi';

const SELECT =
  'rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-xs font-semibold text-foreground outline-none focus:ring-2 focus:ring-accent/30';

const TIER_STYLE: Record<Tier, string> = {
  ROBUST: 'bg-emerald-500/15 text-emerald-500',
  SUGGESTIVE: 'bg-amber-500/15 text-amber-500',
  NONE: 'bg-neutral-500/10 text-neutral-signal',
};

const TierBadge = ({ tier }: { tier: Tier }) => (
  <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${TIER_STYLE[tier]}`}>{tier === 'NONE' ? 'no effect found' : tier.toLowerCase()}</span>
);

const STATE_STYLE = {
  glut: 'text-amber-500',
  squeeze: 'text-sky-500',
  normal: 'text-neutral-signal',
} as const;

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const place = (d: string) => d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

/**
 * Shock Desk: where supply is unusual today, what the data says about the price
 * response, and which cross-commodity links are armed.
 *
 * Every claim carries its evidence tier. ROBUST means it survived the placebo
 * test and Holm correction over the whole battery; SUGGESTIVE means it showed in
 * the sample but did not survive, so it is a lead to check and never a signal to
 * trade on. Farmers only ever receive ROBUST claims, so this page is the only
 * place suggestive results appear. With 30 own-crop tests and 40 cross-crop links
 * the battery is corrected for multiplicity, and the study table also reports the
 * smallest effect each test could have detected.
 */
export default function ShockDesk() {
  const [crop, setCrop] = useState<string>('all');
  const [armedOnly, setArmedOnly] = useState(false);

  const radar = useQuery({ queryKey: ['shock-radar-trader'], queryFn: () => shockApi.radar('trader'), staleTime: 5 * 60 * 1000 });
  const study = useQuery({ queryKey: ['shock-study-trader'], queryFn: () => shockApi.study('trader'), staleTime: 30 * 60 * 1000 });

  const items = useMemo(() => {
    const all = radar.data?.items ?? [];
    return all
      .filter((i) => crop === 'all' || i.crop === crop)
      .sort((a, b) => Math.abs(b.arrivals.z) - Math.abs(a.arrivals.z));
  }, [radar.data, crop]);
  const crops = useMemo(() => Array.from(new Set((radar.data?.items ?? []).map((i) => i.crop))).sort(), [radar.data]);

  const links = useMemo(() => {
    const l = radar.data?.cross_crop?.links ?? [];
    return l.filter((x) => (armedOnly ? x.armed : true) && (crop === 'all' || x.source === crop || x.target === crop));
  }, [radar.data, crop, armedOnly]);

  return (
    <div className="space-y-4">
      <ToolCard
        title="Shock Desk"
        subtitle="Unusual arrivals today, the price response the data supports, and the cross-commodity links they arm"
        icon={<Waves className="h-4.5 w-4.5" />}
        accent="#22d3ee"
      >
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <select value={crop} onChange={(e) => setCrop(e.target.value)} className={`${SELECT} capitalize`}>
            <option value="all">All crops</option>
            {crops.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <input type="checkbox" checked={armedOnly} onChange={(e) => setArmedOnly(e.target.checked)} /> Armed links only
          </label>
          {radar.data?.status === 'OK' && <span className="text-[11px] text-neutral-signal">Arrivals through {radar.data.as_of}</span>}
        </div>

        {radar.isLoading && <LoadingRow label="Reading arrivals against each district’s normal…" />}
        {radar.data?.status === 'UNAVAILABLE' && <RefusalNotice reason={radar.data.reason} />}

        {radar.data?.status === 'OK' && (
          <>
            <ArrivalsTable items={items} />
            <p className="mt-2 text-[11px] leading-relaxed text-neutral-signal">
              A state is flagged when arrivals sit at least 1.5 standard deviations from the trailing norm for that district and crop. Stale readings
              are shown with their age and should not be traded on. The neighbour gap is the price difference to neighbouring districts, expressed
              as the share of this district’s price; it mean-reverts in the sample but does not predict the next week’s direction.
            </p>
          </>
        )}
      </ToolCard>

      {radar.data?.status === 'OK' && radar.data.cross_crop?.status === 'OK' && (
        <ToolCard
          title="Cross-commodity watch"
          subtitle={`${radar.data.cross_crop.n_tested} links tested · ${radar.data.cross_crop.n_robust} robust · ${radar.data.cross_crop.n_suggestive} suggestive`}
          icon={<Waves className="h-4.5 w-4.5" />}
          accent="#a78bfa"
        >
          <LinksTable links={links} />
          <p className="mt-2 text-[11px] leading-relaxed text-neutral-signal">
            Effect is the excess price change of the target crop over its peers after the source crop’s shock, in the districts where both are
            traded. “Armed” means the source crop is in that shock state today in at least one of those districts. A suggestive link is a hypothesis;
            it has not passed the placebo test with the multiplicity correction, so it is not offered to farmers and should not be sized as a trade.
          </p>
        </ToolCard>
      )}

      <ToolCard
        title="Own-crop price response study"
        subtitle="Does the crop’s own price move after an arrivals glut or squeeze? Every test, including the ones that found nothing."
        icon={<Waves className="h-4.5 w-4.5" />}
        accent="#34d399"
      >
        {study.isLoading && <LoadingRow label="Loading the study…" />}
        {study.data?.status === 'UNAVAILABLE' && <RefusalNotice reason={study.data.reason} />}
        {study.data?.status === 'OK' && (
          <>
            <p className="mb-3 text-xs text-foreground">
              {study.data.n_tested} tests over {study.data.data?.from} to {study.data.data?.to}: <b>{study.data.n_robust}</b> robust,{' '}
              <b>{study.data.n_suggestive}</b> suggestive. Holm correction is applied over all {study.data.rules?.holm_over} tests;{' '}
              {study.data.rules?.placebo_draws} placebo draws shift each district’s shocks in time.
            </p>
            <StudyTable rows={(study.data.results ?? []).filter((r) => crop === 'all' || r.crop === crop)} />
          </>
        )}
      </ToolCard>
    </div>
  );
}

function ArrivalsTable({ items }: { items: ShockItem[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[640px] border-collapse text-xs">
        <thead>
          <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
            <th className="px-3 py-2 text-left font-bold">Crop</th>
            <th className="px-3 py-2 text-left font-bold">District</th>
            <th className="px-2 py-2 text-left font-bold">Arrivals</th>
            <th className="px-2 py-2 text-right font-bold">× normal</th>
            <th className="px-2 py-2 text-right font-bold">Price ₹/q</th>
            <th className="px-2 py-2 text-right font-bold">7-day</th>
            <th className="px-2 py-2 text-right font-bold">Neighbour gap</th>
            <th className="px-2 py-2 text-right font-bold">Age</th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={`${i.crop}-${i.district}`} className="border-t border-border">
              <td className="px-3 py-1.5 font-semibold capitalize text-foreground">{i.crop}</td>
              <td className="px-3 py-1.5 text-foreground">{i.district_name}</td>
              <td className={`px-2 py-1.5 font-semibold ${STATE_STYLE[i.arrivals.state]}`}>{cap(i.arrivals.state)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{i.arrivals.times_normal.toFixed(2)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{new Intl.NumberFormat('en-IN').format(Math.round(i.price.modal))}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{formatPct(i.price.change_7d_pct)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{i.gap ? formatPct(i.gap.neighbours_dearer_by_pct, 0) : '—'}</td>
              <td className={`px-2 py-1.5 text-right ${i.arrivals.age_days > 3 ? 'text-amber-500' : 'text-neutral-signal'}`}>{i.arrivals.age_days}d</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={8} className="px-3 py-4 text-center text-neutral-signal">No readings for this selection.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function LinksTable({ links }: { links: CrossLink[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[640px] border-collapse text-xs">
        <thead>
          <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
            <th className="px-3 py-2 text-left font-bold">When</th>
            <th className="px-3 py-2 text-left font-bold">Then</th>
            <th className="px-2 py-2 text-right font-bold">Effect</th>
            <th className="px-2 py-2 text-right font-bold">95% interval</th>
            <th className="px-2 py-2 text-right font-bold">Detectable</th>
            <th className="px-2 py-2 text-right font-bold">Episodes</th>
            <th className="px-2 py-2 text-left font-bold">Evidence</th>
            <th className="px-2 py-2 text-left font-bold">Armed today</th>
          </tr>
        </thead>
        <tbody>
          {links.map((l) => (
            <tr key={`${l.source}-${l.target}-${l.shock}`} className={`border-t border-border ${l.armed && l.tier !== 'NONE' ? 'bg-surface-2/60' : ''}`}>
              <td className="px-3 py-1.5 capitalize text-foreground">{l.source} {l.shock}</td>
              <td className="px-3 py-1.5 capitalize text-foreground">{l.target} price</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{l.effect_pct === null ? '—' : formatPct(l.effect_pct)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{l.ci_pct ? `${formatPct(l.ci_pct[0])} to ${formatPct(l.ci_pct[1])}` : '—'}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{l.min_detectable_pct === null ? '—' : `±${l.min_detectable_pct}%`}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{l.n_episodes}</td>
              <td className="px-2 py-1.5"><TierBadge tier={l.tier} /></td>
              <td className="px-2 py-1.5 text-foreground">{l.armed ? l.armed_districts.map(place).join(', ') : '—'}</td>
            </tr>
          ))}
          {links.length === 0 && (
            <tr>
              <td colSpan={8} className="px-3 py-4 text-center text-neutral-signal">No links for this selection.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function StudyTable({ rows }: { rows: StudyRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[640px] border-collapse text-xs">
        <thead>
          <tr className="bg-surface-2 text-[10px] uppercase tracking-wide text-neutral-signal">
            <th className="px-3 py-2 text-left font-bold">Crop</th>
            <th className="px-2 py-2 text-left font-bold">Shock</th>
            <th className="px-2 py-2 text-right font-bold">Days after</th>
            <th className="px-2 py-2 text-right font-bold">Episodes</th>
            <th className="px-2 py-2 text-right font-bold">Excess vs peers</th>
            <th className="px-2 py-2 text-right font-bold">95% interval</th>
            <th className="px-2 py-2 text-right font-bold">Detectable</th>
            <th className="px-2 py-2 text-right font-bold">Placebo p</th>
            <th className="px-2 py-2 text-right font-bold">Holm p</th>
            <th className="px-2 py-2 text-left font-bold">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.crop}-${r.direction}-${r.horizon_days}`} className="border-t border-border">
              <td className="px-3 py-1.5 font-semibold capitalize text-foreground">{r.crop}</td>
              <td className="px-2 py-1.5 capitalize text-foreground">{r.direction}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{r.horizon_days}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{r.n_episodes}</td>
              <td className="px-2 py-1.5 text-right font-mono text-foreground">{formatPct(r.effect_pct)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{formatPct(r.ci_pct[0])} to {formatPct(r.ci_pct[1])}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">±{r.min_detectable_pct}%</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{r.placebo_p === null ? '—' : r.placebo_p.toFixed(3)}</td>
              <td className="px-2 py-1.5 text-right font-mono text-neutral-signal">{r.holm_p === null ? '—' : r.holm_p.toFixed(3)}</td>
              <td className="px-2 py-1.5"><TierBadge tier={r.tier} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
