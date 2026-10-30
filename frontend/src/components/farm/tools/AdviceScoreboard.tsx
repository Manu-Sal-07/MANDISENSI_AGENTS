'use client';

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Loader2, Trophy } from 'lucide-react';

import { marketChoiceApi, type McWtl } from '@/services/marketChoiceApi';
import { formatRupees } from '@/lib/format';
import { mc } from '@/lib/i18n/marketChoiceCopy';
import type { Lang } from '@/lib/i18n/translations';

const CARD = 'rounded-2xl border border-[var(--farm-line)] bg-white px-4 py-3';

function Bar({ label, w, lang }: { label: string; w: McWtl; lang: Lang }) {
  const parts = [
    { k: 'win', v: w.win, c: 'var(--leaf)' },
    { k: 'tie', v: w.tie, c: '#b9c0c9' },
    { k: 'loss', v: w.loss, c: '#c0392b' },
  ] as const;
  return (
    <div>
      <p className="text-xs font-bold text-[var(--farm-ink-soft)]">{label}</p>
      <div className="mt-1 flex h-4 overflow-hidden rounded-full bg-[var(--farm-line)]" role="img"
        aria-label={parts.map((p) => `${Math.round(p.v * 100)}% ${mc(`score.${p.k}`, lang)}`).join(', ')}>
        {parts.map((p) => p.v > 0 && <div key={p.k} style={{ width: `${p.v * 100}%`, background: p.c }} />)}
      </div>
      <p className="mt-1 flex flex-wrap gap-x-3 text-[11px] font-semibold tabular-nums text-[var(--farm-ink-faint)]">
        {parts.filter((p) => p.v > 0.004).map((p) => (
          <span key={p.k}><i className="mr-1 inline-block h-2 w-2 rounded-sm align-middle" style={{ background: p.c }} />{Math.round(p.v * 100)}% {mc(`score.${p.k}`, lang)}</span>
        ))}
      </p>
    </div>
  );
}

/** Running total of the advice's gain over the nearest mandi, as a small line. */
function Cumulative({ values }: { values: number[] }) {
  const W = 320, H = 70, P = 4;
  const lo = Math.min(0, ...values), hi = Math.max(0, ...values);
  const x = (i: number) => P + (i / Math.max(values.length - 1, 1)) * (W - 2 * P);
  const y = (v: number) => H - P - ((v - lo) / Math.max(hi - lo, 1)) * (H - 2 * P);
  const path = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-1 h-[70px] w-full" role="img" aria-label="running gain">
      <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="var(--farm-line)" strokeDasharray="3 3" />
      <path d={path} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * "Has this advice worked?": the advice replayed on days it was not fitted on. Wins, ties and losses against the two
 * rules a farmer would otherwise use, the share of days the guaranteed minimum held, and the running gain. The floor
 * score is shown as it came out, including when it falls short of the 9 days in 10 we aim for.
 */
export default function AdviceScoreboard({ crop, lang }: { crop: string; lang: Lang }) {
  const [open, setOpen] = useState(false);
  const { data, isFetching } = useQuery({
    queryKey: ['mc-track-record', crop],
    queryFn: () => marketChoiceApi.trackRecord(crop),
    enabled: open,
    staleTime: 30 * 60 * 1000,
  });
  const ok = data?.status === 'OK' ? data : undefined;
  const all = ok?.all;
  const cum = useMemo(() => {
    const out: number[] = [];
    for (const d of ok?.days ?? []) out.push((out[out.length - 1] ?? 0) + d.recommended - d.nearest);
    return out;
  }, [ok]);

  return (
    <div className={CARD}>
      <button type="button" onClick={() => setOpen((v) => !v)} className="farm-focus flex w-full items-center justify-between gap-2" aria-expanded={open}>
        <span className="flex items-center gap-2 text-sm font-bold text-[var(--farm-ink)]">
          <Trophy className="h-4 w-4 text-[var(--leaf)]" /> {mc('score.title', lang)}
        </span>
        <ChevronDown className={`h-4 w-4 text-[var(--farm-ink-faint)] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          {isFetching && !data && <div className="flex items-center gap-2 py-3 text-sm text-[var(--farm-ink-faint)]"><Loader2 className="h-4 w-4 animate-spin" /> {mc('loading', lang)}</div>}
          {data?.status === 'UNAVAILABLE' && <p className="text-sm text-[var(--farm-ink-soft)]">{data.reason}</p>}
          {ok && all && (
            <>
              <p className="text-xs text-[var(--farm-ink-faint)]">{mc('score.sub', lang)} · {mc('score.days', lang, { d: all.days })}</p>
              <Bar label={mc('score.vs_nearest', lang)} w={all.vs_nearest} lang={lang} />
              <Bar label={mc('score.vs_highest', lang)} w={all.vs_highest_yesterday} lang={lang} />
              <div>
                <p className="text-xs font-bold text-[var(--farm-ink-soft)]">{mc('score.floor', lang)}</p>
                <p className="mt-0.5 font-mono text-2xl font-black" style={{ color: all.floor_held_share >= 0.9 ? 'var(--leaf-deep)' : '#8a5a00' }}>
                  {Math.round(all.floor_held_share * 100)}%
                </p>
                <p className="text-[11px] text-[var(--farm-ink-faint)]">{mc('score.floor.note', lang)}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-[var(--farm-ink-soft)]">{mc('score.cum', lang)}</p>
                <Cumulative values={cum} />
                <p className="text-[11px] font-semibold" style={{ color: 'var(--leaf-deep)' }}>{mc('score.gain', lang, { g: formatRupees(all.vs_nearest.mean) })}</p>
              </div>
              {ok.evidence_level === 'limited' && <p className="text-xs font-semibold text-amber-800">{mc('track.limited', lang)}</p>}
            </>
          )}
        </div>
      )}
    </div>
  );
}
