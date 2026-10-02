/**
 * Which visual surface a route belongs to.
 *
 * The product has two audiences with genuinely different needs, and they
 * get different design systems: farmers read outdoors in sunlight on cheap
 * phones and need the bright, high-contrast farm surface; analysts work
 * indoors on dense data and keep the dark terminal. Shared chrome (the
 * header, the bottom nav) asks this which one it is rendering into.
 */
/**
 * Routes that sit on the trading-desk scene (animated night-market backdrop).
 * The terminal is a full-bleed surface of its own and the evaluator pages keep
 * their own look, so neither is listed.
 */
export function isDeskRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return (
    pathname.startsWith('/trader') ||
    pathname.startsWith('/market-explorer') ||
    pathname.startsWith('/intelligence-lab') ||
    pathname.startsWith('/ai-brief') ||
    pathname.startsWith('/terminal')
  );
}

export function isFarmRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return (
    pathname === '/' ||
    pathname.startsWith('/mandi') ||
    pathname.startsWith('/tools') ||
    pathname.startsWith('/prices') ||
    pathname.startsWith('/sell-plan') ||
    pathname.startsWith('/my-money') ||
    pathname.startsWith('/accuracy')
  );
}
