/**
 * Which visual surface a route belongs to.
 *
 * The product has two audiences with genuinely different needs, and they
 * get different design systems: farmers read outdoors in sunlight on cheap
 * phones and need the bright, high-contrast farm surface; analysts work
 * indoors on dense data and keep the dark terminal. Shared chrome (the
 * header, the bottom nav) asks this which one it is rendering into.
 */
export function isFarmRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return pathname === '/' || pathname.startsWith('/mandi');
}
