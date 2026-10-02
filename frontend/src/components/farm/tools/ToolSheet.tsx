'use client';

import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

interface ToolSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  accentColour: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

/**
 * The full-screen panel every tool feature opens into.
 *
 * One shared shell, not eleven bespoke modals: the slide-up motion, the
 * backdrop, the header with an accent-tinted icon badge, and the escape
 * hatches (backdrop tap, Escape key, close button) are exactly the kind of
 * thing that quietly drifts out of sync when copy-pasted per feature, and a
 * farmer should not be able to tell Fair Price Check and Hold-or-Rot were
 * built by different code paths.
 */
export default function ToolSheet({ open, onClose, title, subtitle, accentColour, icon, children }: ToolSheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[70] flex items-end justify-center sm:items-center sm:p-4">
          <motion.div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className="farm-surface relative flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-[2rem] sm:rounded-[2rem]"
            style={{ background: 'var(--farm-paper)' }}
            initial={{ y: '100%', opacity: 0.6 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0.6 }}
            transition={{ type: 'spring', stiffness: 340, damping: 34 }}
          >
            <div className="flex items-start gap-3 border-b border-[var(--farm-line)] px-5 py-4 sm:px-6">
              <span
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
                style={{ background: `${accentColour}1a`, color: accentColour }}
              >
                {icon}
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <h2 className="truncate text-lg font-bold text-[var(--farm-ink)]">{title}</h2>
                {subtitle && (
                  <p className="mt-0.5 text-sm leading-snug text-[var(--farm-ink-faint)]">{subtitle}</p>
                )}
              </div>
              <button
                onClick={onClose}
                aria-label="Close"
                className="farm-focus mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--farm-ink-faint)] transition-colors hover:bg-[var(--farm-line)] hover:text-[var(--farm-ink)]"
              >
                <X className="h-4.5 w-4.5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
