/**
 * "My Money" -- an on-device ledger of sell plans a farmer said they would
 * follow, and what following one actually earned.
 *
 * There is no farmer account system in this build, so the ledger lives in
 * `localStorage` rather than a backend table. That is a real limitation
 * (it does not survive a reinstall or follow the farmer to a new phone),
 * stated plainly here rather than hidden, and the outcome it reports is
 * always resolved against `farmerApi.priceOnDate` -- a real observed mandi
 * print -- never against the plan's own forecast, so the number cannot
 * mark its own homework.
 */

const STORAGE_KEY = 'mandisense-my-money-ledger';

export type PlanChoice = 'sell_today' | 'wait' | 'travel';

export interface SavedPlan {
  id: string;
  createdAt: string;
  commodity: string;
  mandiId: string;
  mandiName: string;
  quantityQuintals: number;
  choice: PlanChoice;
  /** What was recommended, in rupees, for the whole quantity. */
  planTotal: number;
  /** What selling today (right here, right now) would have earned, for
      the same quantity -- the baseline every outcome is measured against. */
  baselineTotal: number;
  /** The date the plan expects the farmer to sell. */
  targetDate: string;
  /** Where the sale should happen, if different from `mandiId`. */
  targetMandiId: string;
  targetMandiName: string;
}

export interface ResolvedOutcome {
  plan: SavedPlan;
  status: 'PENDING' | 'RESOLVED' | 'UNVERIFIABLE';
  actualTotal?: number;
  gainVsBaseline?: number;
}

function readAll(): SavedPlan[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(plans: SavedPlan[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(plans));
  } catch {
    // On-device convenience only; losing it is not fatal.
  }
}

export function listPlans(): SavedPlan[] {
  return readAll().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function savePlan(plan: Omit<SavedPlan, 'id' | 'createdAt'>): SavedPlan {
  const record: SavedPlan = {
    ...plan,
    id: `plan_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
  };
  writeAll([record, ...readAll()]);
  return record;
}

export function clearAll(): void {
  writeAll([]);
}

export function isTargetDateReached(plan: SavedPlan): boolean {
  return new Date(plan.targetDate).getTime() <= Date.now();
}
