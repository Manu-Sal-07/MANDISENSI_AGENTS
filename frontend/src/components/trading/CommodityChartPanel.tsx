'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts';
import { BarChart3, Calendar, TrendingDown, TrendingUp } from 'lucide-react';
import { useCommodityCandles } from '@/hooks/useCommodityCandles';
import { COMMODITIES, type MarketsResponse, type Timeframe } from '@/services/marketDataApi';

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const TIMEFRAMES: { key: Timeframe; label: string }[] = [
  { key: 'week', label: 'Week' },
  { key: 'month', label: 'Month' },
  { key: 'year', label: 'Year' },
];

const COMMODITY_LABELS: Record<string, string> = {
  tomato: 'Tomato',
  onion: 'Onion',
  potato: 'Potato',
  garlic: 'Garlic',
  ginger: 'Ginger',
};

const formatMandi = (mandiId: string) => mandiId.replace('_apmc', '').replace(/_/g, ' ').toUpperCase();

const formatMonth = (ym: string) => {
  const [year, month] = ym.split('-');
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
};

function ChangePill({ label, value }: { label: string; value: number | null }) {
  if (value === null || Number.isNaN(value)) {
    return (
      <div className="bg-[#181c2c]/40 border border-[#252c42] p-2.5 rounded-lg">
        <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold font-mono">{label}</span>
        <span className="text-slate-600 text-sm font-display font-bold block mt-0.5">—</span>
      </div>
    );
  }
  const positive = value >= 0;
  return (
    <div className="bg-[#181c2c]/40 border border-[#252c42] p-2.5 rounded-lg">
      <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold font-mono">{label}</span>
      <span
        className={cx(
          'flex items-center gap-1 text-sm font-display font-bold mt-0.5',
          positive ? 'text-emerald-400' : 'text-rose-400'
        )}
      >
        {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
        {positive ? '+' : ''}
        {value.toFixed(2)}%
      </span>
    </div>
  );
}

type Props = {
  markets: MarketsResponse | null;
  commodity: string;
  onCommodityChange: (commodity: string) => void;
  mandiId: string;
  onMandiChange: (mandiId: string) => void;
  timeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
};

export default function CommodityChartPanel({
  markets,
  commodity,
  onCommodityChange,
  mandiId,
  onMandiChange,
  timeframe,
  onTimeframeChange,
}: Props) {
  const availableMandis = useMemo(() => markets?.markets?.[commodity] ?? [], [markets, commodity]);

  // Keep the selected mandi valid whenever the commodity (or the market
  // list) changes, without ever clobbering a still-valid user selection.
  useEffect(() => {
    if (availableMandis.length === 0) return;
    if (!availableMandis.includes(mandiId)) {
      onMandiChange(availableMandis.includes('kolar_apmc') ? 'kolar_apmc' : availableMandis[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableMandis]);

  const { candles, summary, loading, error } = useCommodityCandles(commodity, mandiId || null, timeframe);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  // Create the chart once and tear it down on unmount; data updates happen
  // separately below so we never rebuild the whole chart just to re-plot.
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
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(129,140,248,0.35)', labelBackgroundColor: '#4338ca' },
        horzLine: { color: 'rgba(129,140,248,0.35)', labelBackgroundColor: '#4338ca' },
      },
      rightPriceScale: { borderColor: '#1e2335' },
      timeScale: { borderColor: '#1e2335', timeVisible: false },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      downColor: '#fb7185',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#fb7185',
      priceScaleId: 'right',
    });
    candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.28 } });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
      color: 'rgba(99,102,241,0.45)',
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // Plot data whenever it changes.
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;

    if (candles.length === 0) {
      candleSeriesRef.current.setData([]);
      volumeSeriesRef.current.setData([]);
      return;
    }

    candleSeriesRef.current.setData(
      candles.map((c) => ({
        time: c.time as unknown as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    volumeSeriesRef.current.setData(
      candles.map((c) => ({
        time: c.time as unknown as UTCTimestamp,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(52,211,153,0.45)' : 'rgba(251,113,133,0.45)',
      }))
    );

    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return (
    <div className="border border-[#1e2335] bg-[#131622]/60 rounded-xl overflow-hidden backdrop-blur-md">
      <div className="px-5 py-4 border-b border-[#1e2335] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-indigo-400" />
          <div>
            <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-indigo-400 font-bold block">
              Historical Price &amp; Volume
            </span>
            <h3 className="font-display text-xs font-black text-white uppercase tracking-wider mt-0.5">
              Commodity Price Chart
            </h3>
          </div>
        </div>

        {/* Mandi selector */}
        <div className="flex items-center gap-1.5 bg-[#171b2c] border border-[#252c42] rounded-lg px-2.5 py-1">
          <span className="font-mono text-[8px] uppercase tracking-wider text-slate-500 font-bold">Mandi</span>
          <select
            value={mandiId}
            onChange={(e) => onMandiChange(e.target.value)}
            className="bg-transparent border-none text-[11px] font-semibold font-display text-white outline-none cursor-pointer pr-1 focus:ring-0"
          >
            {availableMandis.map((m) => (
              <option key={m} value={m} className="bg-[#141724] text-white">
                {formatMandi(m)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Commodity tabs + timeframe toggle */}
      <div className="px-5 pt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          {COMMODITIES.map((c) => (
            <button
              key={c}
              onClick={() => onCommodityChange(c)}
              className={cx(
                'px-3 py-1.5 rounded-lg font-mono text-[9px] font-bold uppercase tracking-wider transition-all border',
                commodity === c
                  ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                  : 'bg-transparent border-[#1e2335] text-slate-500 hover:border-[#2b334d] hover:text-slate-300'
              )}
            >
              {COMMODITY_LABELS[c] ?? c}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 bg-[#171b2c] border border-[#252c42] rounded-lg p-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.key}
              onClick={() => onTimeframeChange(tf.key)}
              className={cx(
                'px-3 py-1 rounded-md font-mono text-[9px] font-bold uppercase tracking-wider transition-all',
                timeframe === tf.key ? 'bg-indigo-500 text-white' : 'text-slate-400 hover:text-white'
              )}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stat strip */}
      <div className="px-5 pt-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5">
        <div className="bg-[#181c2c]/40 border border-[#252c42] p-2.5 rounded-lg">
          <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold font-mono">
            Current
          </span>
          <span className="text-sm font-display font-bold text-white block mt-0.5">
            {summary ? `₹${summary.current_price.toFixed(0)}` : '—'}
          </span>
        </div>
        <ChangePill label="7D" value={summary?.week_change_pct ?? null} />
        <ChangePill label="30D" value={summary?.month_change_pct ?? null} />
        <ChangePill label="1Y" value={summary?.year_change_pct ?? null} />
        <div className="bg-[#181c2c]/40 border border-[#252c42] p-2.5 rounded-lg">
          <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold font-mono flex items-center gap-1">
            <Calendar className="h-2.5 w-2.5" /> Highest Month
          </span>
          <span className="text-sm font-display font-bold text-emerald-400 block mt-0.5">
            {summary ? formatMonth(summary.highest_month.month) : '—'}
          </span>
        </div>
        <div className="bg-[#181c2c]/40 border border-[#252c42] p-2.5 rounded-lg">
          <span className="text-[8px] uppercase tracking-wider text-slate-500 block font-semibold font-mono flex items-center gap-1">
            <BarChart3 className="h-2.5 w-2.5" /> Peak Volume Month
          </span>
          <span className="text-sm font-display font-bold text-indigo-300 block mt-0.5">
            {summary?.highest_volume_month ? formatMonth(summary.highest_volume_month.month) : '—'}
          </span>
        </div>
      </div>

      {/* Chart surface */}
      <div className="px-5 pb-5 pt-4">
        <div className="relative h-[320px] rounded-lg border border-[#1e2335]/60 bg-[#0d0f17]/60 overflow-hidden">
          <div ref={containerRef} className="absolute inset-0" />
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0d0f17]/70 font-mono text-[10px] uppercase tracking-widest text-slate-500">
              Loading price history…
            </div>
          )}
          {!loading && error && (
            <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] uppercase tracking-widest text-rose-400 text-center px-6">
              {error}
            </div>
          )}
          {!loading && !error && candles.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] uppercase tracking-widest text-slate-500">
              No price history available for this corridor
            </div>
          )}
        </div>
        {summary && (
          <p className="mt-2.5 text-[9px] font-mono text-slate-500">
            {summary.data_points.toLocaleString()} daily observations since {summary.history_start} · data as of{' '}
            {summary.as_of} · source: processed mandi price history + daily live sync
          </p>
        )}
      </div>
    </div>
  );
}
