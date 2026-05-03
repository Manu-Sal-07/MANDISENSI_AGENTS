'use client';

import React from 'react';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';
import { AlertCircle, RefreshCcw } from 'lucide-react';
import { logger } from '@/services/logger';

function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-6 text-center bg-white dark:bg-black rounded-3xl border border-zinc-100 dark:border-zinc-900 shadow-sm">
      <div className="max-w-xs space-y-6">
        <div className="w-16 h-16 bg-red-50 dark:bg-red-950/20 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Something went wrong</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            The application encountered an unexpected error. We've logged the issue.
          </p>
        </div>
        <button
          onClick={resetErrorBoundary}
          className="w-full bg-zinc-900 dark:bg-white text-white dark:text-black py-3 rounded-2xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
        >
          <RefreshCcw className="w-4 h-4" />
          Try Again
        </button>
      </div>
    </div>
  );
}

export default function ErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => {
        // Reset app state or clear caches if needed
        window.location.reload();
      }}
      onError={(error, info) => {
        logger.logError('UI Crash Caught by ErrorBoundary', { error, info });
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
