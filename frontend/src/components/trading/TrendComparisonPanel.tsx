'use client';

import React, { useEffect, useRef } from 'react';
import {
  createChart,
  LineSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts';
import { GitCompareArrows } from 'lucide-react';
import { useCommodityComparison } from '@/hooks/useCommodityCandles';
import type { Timeframe } from '@/services/marketDataApi';

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const COMMODITY_LABELS: Record<string, string> = {
  tomato: 'Tomato',
  onion: 'Onion',
  potato: 'Potato',
  garlic: 'Garlic',
  ginger: 'Ginger',
};

// One fixed color per commodity so the legend and the plotted line always
// agree, regardless of ranking order.
const COMMODITY_COLORS: Record<string, string> = {
  tomato: '#fb7185',
  onion: '#a78bfa',
  potato: '#facc15',
  garlic: '#34d399',
  ginger: '#38bdf8',
};

type Props = {
  mandiId: string;
  timeframe: Timeframe;
};

export default function TrendComparisonPanel({ mandiId, timeframe }: Props) {
  const { comparison, loading, error } = useCommodityComparison(mandiId || null, timeframe);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'>[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8b93a7',
        fontFamily: "'Roboto Mono', monospace",
        fontSize: 10,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.035)' },
        horzLines: { color: 'rgba(255,255,255,0.035)' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1e2335' },
      timeScale: { borderColor: '#1e2335' },
    });
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !comparison) return;

    // The set of commodities with data can change between updates, so the
    // previous run's series must be explicitly removed — lightweight-charts
    // has no "clear all series" call, and skipping this stacks duplicate
    // lines on every re-fetch.
    for (const series of seriesRef.current) {
      chart.removeSeries(series);
    }
    seriesRef.current = [];

    for (const commodity of Object.keys(comparison.series)) {
      const series = chart.addSeries(LineSeries, {
        color: COMMODITY_COLORS[commodity] ?? '#94a3b8',
        lineWidth: 2,
        priceFormat: { type: 'custom', formatter: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`, minMove: 0.01 },
      });
      series.setData(
        comparison.series[commodity].map((p) => ({ time: p.time as unknown as UTCTimestamp, value: p.value }))
      );
      seriesRef.current.push(series);
    }
    chart.timeScale().fitContent();
  }, [comparison]);

  return (
    <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md p-5 space-y-4">
      <div className="border-b border-[#1e2335] pb-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompareArrows className="h-4 w-4 text-indigo-400" />
          <div>
            <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">
              Normalized % Change
            </span>
            <h4 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">
              Cross-Commodity Trend Comparison
            </h4>
          </div>
        </div>
      </div>

      <div className="relative h-[220px] rounded-lg border border-[#1e2335]/60 bg-[#0d0f17]/60 overflow-hidden">
        <div ref={containerRef} className="absolute inset-0" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] uppercase tracking-widest text-slate-500">
            Loading comparison…
          </div>
        )}
        {!loading && error && (
          <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] uppercase tracking-widest text-rose-400">
            {error}
          </div>
        )}
      </div>

      {comparison && comparison.ranking.length > 0 && (
        <div className="grid grid-cols-5 gap-2">
          {comparison.ranking.map((r, idx) => (
            <div key={r.commodity} className="bg-[#181c2c]/40 border border-[#252c42] p-2 rounded-lg text-center">
              <div className="flex items-center justify-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: COMMODITY_COLORS[r.commodity] }} />
                <span className="text-[8px] uppercase tracking-wider text-slate-400 font-mono font-bold">
                  {COMMODITY_LABELS[r.commodity] ?? r.commodity}
                </span>
              </div>
              <span
                className={cx(
                  'text-xs font-display font-bold block mt-1',
                  r.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                )}
              >
                {r.change_pct >= 0 ? '+' : ''}
                {r.change_pct.toFixed(1)}%
              </span>
              <span className="text-[7px] text-slate-600 font-mono uppercase tracking-wider">
                {idx === 0 ? 'Top performer' : idx === comparison.ranking.length - 1 ? 'Weakest' : `Rank #${idx + 1}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
