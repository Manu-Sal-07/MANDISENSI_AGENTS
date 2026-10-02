'use client';

import React, { useEffect, useRef, useState } from 'react';
import { animate, useReducedMotion } from 'framer-motion';

/** A rupee figure that counts up from its previous value when it changes —
 *  the one moment of motion on the page that says "this number just updated".
 *  Skipped entirely when the person has asked for reduced motion. */
export default function CountUp({ value, className = '' }: { value: number; className?: string }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(value);
  const from = useRef(value);

  useEffect(() => {
    if (reduce) {
      setShown(value);
      from.current = value;
      return;
    }
    const controls = animate(from.current, value, {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setShown(v),
      onComplete: () => {
        from.current = value;
      },
    });
    return () => controls.stop();
  }, [value, reduce]);

  return (
    <span className={`tabular-nums ${className}`} aria-label={`₹${Math.round(value)}`}>
      ₹{new Intl.NumberFormat('en-IN').format(Math.round(shown))}
    </span>
  );
}
