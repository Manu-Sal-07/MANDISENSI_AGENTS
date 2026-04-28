"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { MetricCard } from "./MetricCard";
import { TrendingUp } from "lucide-react";

interface ChartCardProps {
  currentPrice: number;
  predictedPrice: number;
}

export function ChartCard({ currentPrice, predictedPrice }: ChartCardProps) {
  // Generate some realistic looking sparkline data
  const data = [
    { day: "D-6", price: currentPrice * 0.95 },
    { day: "D-5", price: currentPrice * 0.98 },
    { day: "D-4", price: currentPrice * 0.92 },
    { day: "D-3", price: currentPrice * 0.96 },
    { day: "D-2", price: currentPrice * 0.99 },
    { day: "D-1", price: currentPrice * 1.01 },
    { day: "Now", price: currentPrice },
    { day: "D+7", price: predictedPrice, isFuture: true },
  ];

  const isUp = predictedPrice >= currentPrice;

  return (
    <MetricCard 
      title="Price Trend Forecast" 
      icon={<TrendingUp className="w-4 h-4" />} 
      className="col-span-full h-48"
      glowColor={isUp ? "green" : "red"}
    >
      <div className="absolute top-4 right-4 text-right">
        <span className="text-2xl font-black text-foreground">₹{currentPrice}</span>
        <div className={`text-xs font-bold ${isUp ? 'text-emerald-500' : 'text-rose-500'}`}>
          {isUp ? '↑' : '↓'} Expected ₹{predictedPrice.toFixed(0)}
        </div>
      </div>

      <div className="w-full h-full mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis domain={['auto', 'auto']} axisLine={false} tickLine={false} tick={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
              itemStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
            />
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke={isUp ? "#22c55e" : "#ef4444"} 
              strokeWidth={3} 
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                if (payload.day === "Now") return <circle cx={cx} cy={cy} r={4} fill="#fff" stroke={isUp ? "#22c55e" : "#ef4444"} strokeWidth={2} />;
                if (payload.day === "D+7") return <circle cx={cx} cy={cy} r={4} fill={isUp ? "#22c55e" : "#ef4444"} stroke="none" />;
                return <circle cx={cx} cy={cy} r={0} />;
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </MetricCard>
  );
}
