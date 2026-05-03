import React from 'react';
import { TrendingDown, TrendingUp, Info, ChevronRight } from 'lucide-react';
import DecisionBadge from './DecisionBadge';

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
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
            {name} Mandi
          </h1>
          <p className="text-zinc-500 font-medium mt-1">Market Dynamics & Real-time Decisions</p>
        </div>
      </header>

      <div className="grid gap-4">
        {commodities.map((item) => (
          <div 
            key={item.name}
            className="group bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 rounded-3xl p-6 hover:shadow-xl transition-all duration-300"
          >
            <div className="flex justify-between items-start mb-6">
              <div className="flex gap-4 items-center">
                <div className="w-14 h-14 rounded-2xl bg-zinc-50 dark:bg-zinc-800 flex items-center justify-center text-3xl">
                  {item.name === 'Tomato' ? '🍅' : item.name === 'Onion' ? '🧅' : '🥔'}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">{item.name}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-sm font-bold text-zinc-400 tracking-tight">₹{item.price}/quintal</span>
                    <span className={`flex items-center gap-0.5 text-xs font-black ${
                      item.trend === 'UP' ? 'text-emerald-500' : 'text-red-500'
                    }`}>
                      {item.trend === 'UP' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {item.prediction}
                    </span>
                  </div>
                </div>
              </div>
              <DecisionBadge decision={item.decision} />
            </div>

            <div className="bg-zinc-50 dark:bg-zinc-950/50 rounded-2xl p-4 border border-zinc-100 dark:border-zinc-900">
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  <Info size={16} className="text-orange-500" />
                </div>
                <div>
                  <p className="text-sm font-bold text-zinc-800 dark:text-zinc-200">Recommended Action</p>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 font-medium leading-relaxed">
                    {item.reason}
                  </p>
                </div>
              </div>
              
              <div className="flex gap-6 mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-900">
                <div>
                  <p className="text-[10px] font-black uppercase text-zinc-400 tracking-widest">Confidence</p>
                  <p className="text-xs font-bold text-zinc-700 dark:text-zinc-300 mt-0.5">{item.confidence}</p>
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase text-zinc-400 tracking-widest">Risk Level</p>
                  <p className="text-xs font-bold text-zinc-700 dark:text-zinc-300 mt-0.5">{item.risk}</p>
                </div>
              </div>
            </div>
            
            <button className="w-full mt-4 py-3 flex items-center justify-center gap-2 text-zinc-400 group-hover:text-orange-500 transition-colors text-xs font-bold uppercase tracking-widest">
              View Detailed Analytics <ChevronRight size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MandiDetail;
