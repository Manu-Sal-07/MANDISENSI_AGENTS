export type Decision = 'SELL' | 'HOLD' | 'WAIT';
export type Trend = 'UP' | 'DOWN' | 'STABLE';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type Confidence = number;

export interface MandiOpportunity {
  id: string;
  mandi: string;
  distance: string;
  best_crop: string;
  decision: Decision;
  trend: string;
  trend_type: Trend;
  tags: string[];
  confidence: number;
  profit_window: string;
  highlight_badge?: string;
  price_change_pct?: number;
  risk_level?: RiskLevel;
}

export interface QueryResponse {
  decision: Decision;
  /** Which of ADVISED / ABSTAINED / UNAVAILABLE produced `decision` — see
   * `CallCard.resolveCall`. Without this, "the policy declined to call it"
   * and "there is no forecast at all" both arrive as the same string
   * "WAIT" and render as the same confident tile. */
  call_type?: 'ADVISED' | 'ABSTAINED' | 'UNAVAILABLE' | null;
  abstention_reason?: string | null;
  summary: string;
  reasoning: string;
  market_insight: string;
  metadata: {
    commodity: string;
    mandi_id: string;
    confidence: number;
  }
}

export interface Outlook {
  horizon: string;
  trend: string;
  trend_type: Trend;
}

export interface CommodityInsight {
  id: string;
  name: string;
  decision: Decision;
  confidence: Confidence;
  profit_window: string;
  outlook: Outlook[];
  reasoning: string[];
}

export interface MandiDetail {
  id: string;
  name: string;
  arrivals: 'HIGH' | 'MEDIUM' | 'LOW';
  demand: 'HIGH' | 'MEDIUM' | 'LOW';
  overall_trend: 'FALLING' | 'RISING' | 'STABLE';
  commodities: CommodityInsight[];
}

export const MOCK_OPPORTUNITIES: MandiOpportunity[] = [
  {
    id: '1',
    mandi: 'Kolar',
    distance: '12 km',
    best_crop: 'Tomato',
    decision: 'SELL',
    trend: 'Prices may drop slightly',
    trend_type: 'DOWN',
    tags: ['High Arrival', 'Low Demand'],
    confidence: 0.85,
    profit_window: 'Sell within 2 days',
    highlight_badge: 'Best Opportunity',
    price_change_pct: -2.4,
    risk_level: 'LOW'
  },
  {
    id: '2',
    mandi: 'Chintamani',
    distance: '24 km',
    best_crop: 'Onion',
    decision: 'HOLD',
    trend: 'Prices recovering',
    trend_type: 'UP',
    tags: ['Low Supply', 'Export Demand'],
    confidence: 0.92,
    profit_window: 'Hold for 5 days',
    highlight_badge: 'High Potential',
    price_change_pct: 4.2,
    risk_level: 'MEDIUM'
  }
];
