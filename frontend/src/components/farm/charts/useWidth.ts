import { useEffect, useRef, useState } from 'react';

/** Width of an element, tracked as it resizes, so a chart can draw in real
 *  pixels (crisp 2px lines, readable labels) instead of scaling a viewBox. */
export function useWidth<T extends HTMLElement>(initial = 340) {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(initial);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(Math.round(el.getBoundingClientRect().width) || initial);
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width) || initial));
    observer.observe(el);
    return () => observer.disconnect();
  }, [initial]);
  return [ref, width] as const;
}
