import {
  Activity,
  FlaskConical,
  Gauge,
  History,
  Network,
  Route,
  Scale,
  Wallet,
  type LucideIcon,
} from 'lucide-react';

export type ToolAccent = 'cyan' | 'violet' | 'amber' | 'green';

export interface TraderTool {
  slug: string;
  href: string;
  title: string;
  blurb: string;
  group: 'Market scan' | 'Risk and regime' | 'Forecasting';
  accent: ToolAccent;
  photo: string;
  icon: LucideIcon;
  /** Needs the shared commodity + mandi focus. */
  focus: boolean;
}

/**
 * The eight trader tools, one page each. The hub, the page shell and the
 * previous/next navigation all read this list so the set stays consistent.
 */
export const TRADER_TOOLS: TraderTool[] = [
  {
    slug: 'spreads',
    href: '/trader-tools/spreads',
    title: 'Mandi Spread Scanner',
    blurb: 'Net margin expected to still be there on arrival, not today’s gap.',
    group: 'Market scan',
    accent: 'cyan',
    photo: 'desk-yard',
    icon: Scale,
    focus: false,
  },
  {
    slug: 'gap-arbitrage',
    href: '/trader-tools/gap-arbitrage',
    title: 'Gap Arbitrage',
    blurb: 'Same-crop price gaps between districts, projected to a trip length net of transport.',
    group: 'Market scan',
    accent: 'green',
    photo: 'desk-truck',
    icon: Route,
    focus: false,
  },
  {
    slug: 'transmission',
    href: '/trader-tools/transmission',
    title: 'Cross-Commodity Transmission',
    blurb: 'Which crop’s shock moves another, with every tested link and how much it could detect.',
    group: 'Market scan',
    accent: 'violet',
    photo: 'desk-hall',
    icon: Network,
    focus: false,
  },
  {
    slug: 'volatility',
    href: '/trader-tools/volatility',
    title: 'Volatility & Regime',
    blurb: 'Where today’s volatility sits against this series’ own history.',
    group: 'Risk and regime',
    accent: 'amber',
    photo: 'desk-night',
    icon: Activity,
    focus: true,
  },
  {
    slug: 'scenarios',
    href: '/trader-tools/scenarios',
    title: 'Evidence-Based Scenarios',
    blurb: 'What happened, historically, after conditions like today’s.',
    group: 'Risk and regime',
    accent: 'violet',
    photo: 'desk-unload',
    icon: FlaskConical,
    focus: true,
  },
  {
    slug: 'positions',
    href: '/trader-tools/positions',
    title: 'Position Book',
    blurb: 'Exposure priced against what you actually hold.',
    group: 'Risk and regime',
    accent: 'green',
    photo: 'desk-scale',
    icon: Wallet,
    focus: false,
  },
  {
    slug: 'analogs',
    href: '/trader-tools/analogs',
    title: 'Historical Analogs',
    blurb: 'When has this market looked like this before, and what came next?',
    group: 'Forecasting',
    accent: 'cyan',
    photo: 'mandi-yard',
    icon: History,
    focus: true,
  },
  {
    slug: 'forward-price',
    href: '/trader-tools/forward-price',
    title: 'Forward Price Calculator',
    blurb: 'A forward price range for your horizon, from the calibrated forecast.',
    group: 'Forecasting',
    accent: 'amber',
    photo: 'desk-tomatoes',
    icon: Gauge,
    focus: true,
  },
];

export const TOOL_GROUPS: TraderTool['group'][] = ['Market scan', 'Risk and regime', 'Forecasting'];

export const toolBySlug = (slug: string) => TRADER_TOOLS.find((t) => t.slug === slug);
