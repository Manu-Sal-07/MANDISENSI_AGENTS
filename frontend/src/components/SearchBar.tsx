'use client';

import React, { useState } from 'react';
import { Search, Loader2, Mic, ArrowRight } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

// Every suggestion names a commodity *and* a mandi, because the query engine
// needs both to give an answer. Earlier copy here ("Best time to sell potatoes
// this week?") named no market and could only ever come back asking for one.
const SUGGESTIONS = [
  'Should I sell tomatoes in Kolar today?',
  'Can I hold my onion stock in Bengaluru?',
  'Best time to sell potatoes in Hoskote?',
];

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query);
  };

  return (
    <div className="mx-auto w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="relative">
        <div
          className="relative flex items-center rounded-2xl border bg-surface-1 transition-all"
          style={{
            borderColor: focused ? 'color-mix(in oklch, var(--accent) 45%, transparent)' : 'var(--surface-border)',
            boxShadow: focused ? '0 0 0 4px var(--accent-soft)' : 'none',
          }}
        >
          <div className="pointer-events-none flex items-center pl-4">
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin text-accent-strong" />
            ) : (
              <Search className="h-5 w-5 text-neutral-signal" />
            )}
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Ask a trading question…"
            className="w-full bg-transparent py-4 pl-3 pr-2 text-[15px] font-medium text-foreground outline-none placeholder:text-neutral-signal"
          />
          <button
            type="button"
            className="hidden shrink-0 p-2 text-neutral-signal transition-colors hover:text-accent-strong sm:block"
            title="Ask by voice"
          >
            <Mic className="h-5 w-5" />
          </button>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="btn-primary m-1.5 shrink-0 !rounded-xl !px-5"
          >
            <span className="hidden sm:inline">Ask AI</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </form>

      <div className="mt-3 flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSearch(s)}
            disabled={isLoading}
            className="chip disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SearchBar;
