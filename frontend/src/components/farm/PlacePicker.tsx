'use client';

import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, Crosshair, Loader2, MapPin, X } from 'lucide-react';

import { useFarm } from '@/context/FarmContext';
import { useLanguage } from '@/context/LanguageContext';
import { districtName, say } from '@/lib/i18n/farmCopy';
import { farmerApi } from '@/services/farmerApi';

/**
 * The one control that decides what every number on the screen means: which
 * district's prices these are. A bottom sheet on a phone, with "use my
 * location" as the first option and a plain list beneath it for anyone who has
 * location switched off.
 */
export default function PlacePicker() {
  const { district, setDistrict, catalog, districtInfo } = useFarm();
  const { lang } = useLanguage();
  const [open, setOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const locate = () => {
    if (!navigator.geolocation) {
      setDenied(true);
      return;
    }
    setLocating(true);
    setDenied(false);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const nearest = await farmerApi.nearestDistrict(coords.latitude, coords.longitude);
          setDistrict(nearest.district);
          setOpen(false);
        } catch {
          setDenied(true);
        } finally {
          setLocating(false);
        }
      },
      () => {
        setDenied(true);
        setLocating(false);
      },
      { timeout: 8000 }
    );
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className="farm-focus flex min-w-0 items-center gap-3 rounded-xl text-left"
      >
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl" style={{ background: 'var(--leaf-wash)' }}>
          <MapPin className="h-5 w-5" style={{ color: 'var(--leaf)' }} />
        </span>
        <span className="min-w-0">
          <span className="flex items-center gap-1 truncate text-base font-bold leading-tight text-[var(--farm-ink)]">
            {districtInfo ? districtName(districtInfo, lang) : '…'}
            <ChevronDown className="h-4 w-4 shrink-0 text-[var(--farm-ink-faint)]" />
          </span>
          <span className="block truncate text-xs text-[var(--farm-ink-faint)]">{say('place.pick', lang)}</span>
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[70] flex items-end justify-center bg-black/35 sm:items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={say('place.pick', lang)}
              className="w-full max-w-md rounded-t-3xl bg-white p-5 shadow-2xl sm:rounded-3xl"
              initial={{ y: 60, opacity: 0.6 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 60, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 320, damping: 32 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between">
                <h2 className="farm-display text-xl text-[var(--farm-ink)]">{say('place.pick', lang)}</h2>
                <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="farm-focus flex h-10 w-10 items-center justify-center rounded-full hover:bg-[var(--farm-paper-warm)]">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <button
                type="button"
                onClick={locate}
                disabled={locating}
                className="farm-focus mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--leaf)] px-4 py-3.5 text-base font-bold text-white disabled:opacity-70"
              >
                {locating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Crosshair className="h-4 w-4" />}
                {locating ? say('place.locating', lang) : say('place.locate', lang)}
              </button>
              {denied && <p className="mt-2 text-sm font-semibold text-[var(--call-sell)]">{say('place.denied', lang)}</p>}

              <ul className="mt-4 space-y-2">
                {catalog?.districts.map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setDistrict(d.id);
                        setOpen(false);
                      }}
                      className="farm-focus flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left"
                      style={{
                        borderColor: d.id === district ? 'var(--leaf)' : 'var(--farm-line)',
                        background: d.id === district ? 'var(--leaf-wash)' : 'var(--farm-paper)',
                      }}
                    >
                      <span>
                        <span className="block text-base font-bold text-[var(--farm-ink)]">{districtName(d, lang)}</span>
                        <span className="block text-xs text-[var(--farm-ink-faint)]">{d.mandis.length} {lang === 'kn' ? 'ಮಂಡಿಗಳು' : lang === 'hi' ? 'मंडियाँ' : 'mandis'}</span>
                      </span>
                      {d.id === district && <Check className="h-5 w-5 text-[var(--leaf)]" />}
                    </button>
                  </li>
                ))}
              </ul>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
