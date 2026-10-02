'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Award,
  Bell,
  CalendarClock,
  HandCoins,
  MapPinned,
  PackageX,
  Sprout,
  Truck,
  Wallet,
  Waves,
} from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

import FairPriceTool from './FairPriceTool';
import HarvestTool from './HarvestTool';
import HoldOrRotTool from './HoldOrRotTool';
import SeasonalMemoryTool from './SeasonalMemoryTool';
import WhereToSellTool from './WhereToSellTool';
import SupplySignalTool from './SupplySignalTool';
import TrackRecordTool from './TrackRecordTool';
import CropPlanningTool from './CropPlanningTool';
import AlertsTool from './AlertsTool';
import TruckShareTool from './TruckShareTool';

type ToolKey =
  | 'fair_price' | 'harvest' | 'hold_or_rot' | 'seasonal_memory' | 'where_to_sell'
  | 'supply_signal' | 'track_record' | 'crop_planning' | 'alerts' | 'truck_share';

const TILES: Array<{ key: ToolKey; icon: React.ReactNode; colour: string; wash: string }> = [
  { key: 'fair_price', icon: <HandCoins className="h-6 w-6" />, colour: 'var(--tomato)', wash: 'var(--tomato-wash)' },
  { key: 'harvest', icon: <Wallet className="h-6 w-6" />, colour: 'var(--leaf-deep)', wash: 'var(--leaf-wash)' },
  { key: 'hold_or_rot', icon: <PackageX className="h-6 w-6" />, colour: 'var(--turmeric)', wash: 'var(--turmeric-wash)' },
  { key: 'seasonal_memory', icon: <CalendarClock className="h-6 w-6" />, colour: 'var(--soil)', wash: '#f2ece3' },
  { key: 'where_to_sell', icon: <MapPinned className="h-6 w-6" />, colour: '#2f6fed', wash: '#e8eefd' },
  { key: 'supply_signal', icon: <Waves className="h-6 w-6" />, colour: '#2f8fd9', wash: '#e5f3fb' },
  { key: 'track_record', icon: <Award className="h-6 w-6" />, colour: '#7a4fd1', wash: '#efe9fb' },
  { key: 'crop_planning', icon: <Sprout className="h-6 w-6" />, colour: 'var(--leaf)', wash: 'var(--leaf-wash)' },
  { key: 'alerts', icon: <Bell className="h-6 w-6" />, colour: '#d1874f', wash: '#faece0' },
  { key: 'truck_share', icon: <Truck className="h-6 w-6" />, colour: '#5c6b8a', wash: '#eaedf2' },
];

/**
 * The farmer tools launcher grid.
 *
 * Nine features that all need the same two questions answered ("which
 * crop", "which mandi") share one context (`ToolContext`) rather than
 * asking again per tile, and each opens as a full-screen sheet rather than
 * navigating to a new route — this is a set of quick lookups a farmer
 * dips in and out of, not a set of destinations to browse between.
 */
export default function ToolsGrid() {
  const { t } = useLanguage();
  const [openTool, setOpenTool] = useState<ToolKey | null>(null);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {TILES.map((tile, index) => (
          <motion.button
            key={tile.key}
            type="button"
            onClick={() => setOpenTool(tile.key)}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.35 }}
            whileTap={{ scale: 0.96 }}
            className="farm-focus farm-row flex flex-col items-start gap-2.5 p-4 text-left"
          >
            <span
              className="flex h-11 w-11 items-center justify-center rounded-2xl"
              style={{ background: tile.wash, color: tile.colour }}
            >
              {tile.icon}
            </span>
            <span>
              <span className="block text-sm font-bold leading-tight text-[var(--farm-ink)]">
                {t(`tool.${tile.key}.title`)}
              </span>
              <span className="mt-0.5 block text-xs leading-snug text-[var(--farm-ink-faint)]">
                {t(`tool.${tile.key}.desc`)}
              </span>
            </span>
          </motion.button>
        ))}
      </div>

      <FairPriceTool open={openTool === 'fair_price'} onClose={() => setOpenTool(null)} />
      <HarvestTool open={openTool === 'harvest'} onClose={() => setOpenTool(null)} />
      <HoldOrRotTool open={openTool === 'hold_or_rot'} onClose={() => setOpenTool(null)} />
      <SeasonalMemoryTool open={openTool === 'seasonal_memory'} onClose={() => setOpenTool(null)} />
      <WhereToSellTool open={openTool === 'where_to_sell'} onClose={() => setOpenTool(null)} />
      <SupplySignalTool open={openTool === 'supply_signal'} onClose={() => setOpenTool(null)} />
      <TrackRecordTool open={openTool === 'track_record'} onClose={() => setOpenTool(null)} />
      <CropPlanningTool open={openTool === 'crop_planning'} onClose={() => setOpenTool(null)} />
      <AlertsTool open={openTool === 'alerts'} onClose={() => setOpenTool(null)} />
      <TruckShareTool open={openTool === 'truck_share'} onClose={() => setOpenTool(null)} />
    </>
  );
}
