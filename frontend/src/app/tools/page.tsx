'use client';

import React from 'react';
import { motion } from 'framer-motion';
import ToolsGrid from '@/components/farm/tools/ToolsGrid';
import { ToolProvider } from '@/context/ToolContext';
import { useLanguage } from '@/context/LanguageContext';

function ToolsPageBody() {
  const { t } = useLanguage();
  return (
    <div className="farm-surface min-h-screen pb-28">
      <main className="mx-auto max-w-3xl px-4 pb-10 pt-6 lg:max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1 className="farm-display text-2xl text-[var(--farm-ink)] sm:text-3xl">{t('tools.title')}</h1>
          <p className="mt-1 text-sm text-[var(--farm-ink-faint)]">{t('tools.subtitle')}</p>
        </motion.div>

        <div className="mt-6">
          <ToolsGrid />
        </div>
      </main>
    </div>
  );
}

export default function ToolsPage() {
  return (
    <ToolProvider>
      <ToolsPageBody />
    </ToolProvider>
  );
}
