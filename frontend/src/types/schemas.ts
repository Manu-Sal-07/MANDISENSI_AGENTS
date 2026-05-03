import { z } from 'zod';

export const MandiOpportunitySchema = z.object({
  id: z.string().default(() => Math.random().toString(36).substring(7)),
  mandi: z.string().default('Unknown Mandi'),
  distance: z.union([z.string(), z.number()]).transform(val => typeof val === 'number' ? `${val} km` : val).default('N/A'),
  best_crop: z.string().default('Crop'),
  decision: z.enum(['SELL', 'HOLD', 'WAIT']).default('WAIT'),
  trend: z.string().optional().default('Stable'),
  trend_type: z.enum(['UP', 'DOWN', 'STABLE']).default('STABLE'),
  tags: z.array(z.string()).default([]),
  confidence: z.number().default(0.5),
  profit_window: z.string().default('Immediate'),
  highlight_badge: z.string().optional(),
  price_change_pct: z.number().optional(),
  risk_level: z.enum(['LOW', 'MEDIUM', 'HIGH']).optional(),
});

export const MandiDetailSchema = z.object({
  id: z.string(),
  name: z.string(),
  arrivals: z.enum(['HIGH', 'MEDIUM', 'LOW']).default('MEDIUM'),
  demand: z.enum(['HIGH', 'MEDIUM', 'LOW']).default('MEDIUM'),
  overall_trend: z.enum(['FALLING', 'RISING', 'STABLE']).default('STABLE'),
  commodities: z.array(z.object({
    id: z.string(),
    name: z.string(),
    decision: z.enum(['SELL', 'WAIT']),
    confidence: z.enum(['HIGH', 'MEDIUM', 'LOW']),
    profit_window: z.string(),
    outlook: z.array(z.object({
      horizon: z.string(),
      trend: z.string(),
      trend_type: z.enum(['UP', 'DOWN', 'STABLE']),
    })),
    reasoning: z.array(z.string()).default([]),
  })).default([]),
});

export type ValidMandiOpportunity = z.infer<typeof MandiOpportunitySchema>;
export type ValidMandiDetail = z.infer<typeof MandiDetailSchema>;
