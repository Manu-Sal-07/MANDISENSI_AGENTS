/**
 * Shared number formatting for the farmer surface.
 *
 * Extracted here because it was independently redefined in `CallCard.tsx`,
 * `ForecastPanel.tsx` and the mandi detail page — three copies that could
 * silently drift (one already rounds differently from another). New tool
 * panels import this instead of writing a fourth copy.
 */

export const formatRupees = (value?: number | null): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `₹${new Intl.NumberFormat('en-IN').format(Math.round(value))}`;
};

export const formatSignedPct = (value?: number | null): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
};

export const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  } catch {
    return value;
  }
};
