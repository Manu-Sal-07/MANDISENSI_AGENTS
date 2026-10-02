'use client';

import React, { useState } from 'react';
import { useMarketList } from '@/hooks/useCommodityCandles';
import type { Timeframe } from '@/services/marketDataApi';
import CommodityChartPanel from './CommodityChartPanel';
import TrendComparisonPanel from './TrendComparisonPanel';

/**
 * The trader-facing commodity chart feature: a candlestick + volume chart
 * per commodity, and a normalized trend comparison across all five, sharing
 * one mandi/timeframe selection so both views always describe the same
 * corridor and window.
 */
export default function TradingSection() {
  const { markets } = useMarketList();
  const [commodity, setCommodity] = useState('tomato');
  const [mandiId, setMandiId] = useState('kolar_apmc');
  const [timeframe, setTimeframe] = useState<Timeframe>('month');

  return (
    <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
      <div className="xl:col-span-3">
        <CommodityChartPanel
          markets={markets}
          commodity={commodity}
          onCommodityChange={setCommodity}
          mandiId={mandiId}
          onMandiChange={setMandiId}
          timeframe={timeframe}
          onTimeframeChange={setTimeframe}
        />
      </div>
      <div className="xl:col-span-2">
        <TrendComparisonPanel mandiId={mandiId} timeframe={timeframe} />
      </div>
    </div>
  );
}
