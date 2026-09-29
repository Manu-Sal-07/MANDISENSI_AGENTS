import React from 'react';
import { TrendingDown, TrendingUp, Info, ChevronRight } from 'lucide-react';
import DecisionBadge from './DecisionBadge';
import CommodityGlyph from './CommodityGlyph';

interface Commodity {
  name: string;
  price: string;
  trend: 'UP' | 'DOWN' | 'STABLE';
  prediction: string;
  decision: 'SELL' | 'HOLD' | 'WAIT';
  reason: string;
  confidence: 'High' | 'Medium' | 'Low';
  risk: 'High' | 'Medium' | 'Low';
}

interface MandiDetailProps {
  name: string;
  commodities: Commodity[];
}

const MandiDetail: React.FC<MandiDetailProps> = ({ name, commodities }) => {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {name} Mandi
        </h1>
        <p className="mt-1 font-medium text-neutral-signal">Market dynamics &amp; real-time decisions</p>
      </header>

      <div className="grid gap-4">
        {commodities.map((item) => (
          <div key={item.name} className="elite-card elite-card-hover rounded-3xl p-6">
            <div className="mb-6 flex items-start justify-between">
              <div className="flex items-center gap-4">
                <CommodityGlyph name={item.name} size="md" />
                <div>
                  <h3 className="text-xl font-bold text-foreground">{item.name}</h3>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="font-mono text-sm font-bold tabular-nums text-neutral-signal">
                      ₹{item.price}/quintal
                    </span>
                    <span className={`flex items-center gap-0.5 text-xs font-black ${item.trend === 'UP' ? 'text-bullish' : 'text-bearish'}`}>
                      {item.trend === 'UP' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {item.prediction}
                    </span>
                  </div>
                </div>
              </div>
              <DecisionBadge decision={item.decision} />
            </div>

            <div className="rounded-2xl border border-border bg-surface-2/60 p-4">
              <div className="flex items-start gap-3">
                <Info size={16} className="mt-1 shrink-0 text-accent-strong" />
                <div>
                  <p className="text-sm font-bold text-foreground">Recommended Action</p>
                  <p className="mt-1 text-sm font-medium leading-relaxed text-neutral-signal">
                    {item.reason}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex gap-6 border-t border-border pt-4">
                <div>
                  <p className="label-caps text-[9.5px]">Confidence</p>
                  <p className="mt-0.5 text-xs font-bold text-foreground">{item.confidence}</p>
                </div>
                <div>
                  <p className="label-caps text-[9.5px]">Risk Level</p>
                  <p className="mt-0.5 text-xs font-bold text-foreground">{item.risk}</p>
                </div>
              </div>
            </div>

            <button className="group mt-4 flex w-full items-center justify-center gap-2 py-3 text-xs font-bold uppercase tracking-widest text-neutral-signal transition-colors hover:text-accent-strong">
              View Detailed Analytics
              <ChevronRight size={14} className="transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MandiDetail;
