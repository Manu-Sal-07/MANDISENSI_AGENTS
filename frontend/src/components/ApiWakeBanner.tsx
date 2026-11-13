'use client';

import { useEffect, useState } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// The API runs on a free plan that puts it to sleep when idle, and waking it can take several minutes. Without a word of explanation the
// pages just sit empty and look broken. This pings the health endpoint on load: if the server answers quickly nothing is shown; if not,
// it says what is happening, keeps trying, and reloads the page once the server is ready so the content fills in by itself.
const SLOW_AFTER_MS = 3500;
const POLL_EVERY_MS = 5000;
const GIVE_UP_AFTER_MS = 10 * 60 * 1000;

async function reachable(timeoutMs: number): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE_URL}/v1/health`, { signal: controller.signal, cache: 'no-store' });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

export default function ApiWakeBanner() {
  const [waking, setWaking] = useState(false);
  const [gaveUp, setGaveUp] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let wasWaking = false;
    const started = Date.now();

    const run = async () => {
      const first = await reachable(SLOW_AFTER_MS);
      if (cancelled || first) return;
      wasWaking = true;
      setWaking(true);
      while (!cancelled && Date.now() - started < GIVE_UP_AFTER_MS) {
        if (await reachable(POLL_EVERY_MS * 2)) {
          if (!cancelled && wasWaking) window.location.reload();
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_EVERY_MS));
      }
      if (!cancelled) setGaveUp(true);
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!waking) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="mx-auto mt-3 w-[calc(100%-2rem)] max-w-3xl rounded-xl border border-yellow-500/40 bg-yellow-500/15 px-4 py-3 text-sm text-foreground"
    >
      {gaveUp ? (
        <span>
          The server is still not answering. Please try again in a few minutes.{' '}
          <button type="button" className="underline" onClick={() => window.location.reload()}>
            Reload
          </button>
        </span>
      ) : (
        <span>
          <strong>Waking the server.</strong> It sleeps when nobody has used it for a while, so the first visit can take up to five minutes.
          This page will load by itself when it is ready.
        </span>
      )}
    </div>
  );
}
