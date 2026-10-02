'use client';

import PageHero from '@/components/farm/PageHero';
import { Wrench } from 'lucide-react';
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
        <PageHero photo="farmer-smile" title={t('tools.title')} subtitle={t('tools.subtitle')} icon={<Wrench className="h-7 w-7" />} produce={['tomato', 'ginger', 'potato']} />

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
