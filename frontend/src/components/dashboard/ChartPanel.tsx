"use client";

import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area } from "recharts";
import { TrendingUp, Activity } from "lucide-react";

interface ChartPanelProps {
  currentPrice: number;
  predictedPrice: number;
}

export function ChartPanel({ currentPrice, predictedPrice }: ChartPanelProps) {
  const isUp = predictedPrice >= currentPrice;
  
  const data = [
    { name: "Mon", price: currentPrice * 0.94, predicted: currentPrice * 0.94 },
    { name: "Tue", price: currentPrice * 0.97, predicted: currentPrice * 0.97 },
    { name: "Wed", price: currentPrice * 0.92, predicted: currentPrice * 0.92 },
    { name: "Thu", price: currentPrice * 0.96, predicted: currentPrice * 0.96 },
    { name: "Fri", price: currentPrice * 0.99, predicted: currentPrice * 0.99 },
    { name: "Sat", price: currentPrice * 1.02, predicted: currentPrice * 1.02 },
    { name: "Sun", price: currentPrice, predicted: currentPrice },
    { name: "Future", price: null, predicted: predictedPrice },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-slate-900/40 border border-white/10 rounded-3xl p-6 h-[400px] flex flex-col backdrop-blur-md"
    >
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white uppercase tracking-wider">Price Projection</h2>
        </div>
        <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-xs text-slate-400 font-medium">Actual</span>
            </div>
            <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-emerald-500 border-2 border-dashed border-emerald-500" />
                <span className="text-xs text-slate-400 font-medium">Predicted</span>
            </div>
        </div>
      </div>

      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis 
              dataKey="name" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#64748b', fontSize: 12 }} 
            />
            <YAxis 
              domain={['auto', 'auto']} 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#64748b', fontSize: 12 }} 
              tickFormatter={(v) => `₹${v}`}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#020617', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
              itemStyle={{ color: '#fff' }}
            />
            <Area type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorPrice)" />
            <Area type="monotone" dataKey="predicted" stroke="#10b981" strokeWidth={3} strokeDasharray="5 5" fillOpacity={1} fill="url(#colorPred)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
