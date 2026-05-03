'use client';

import React, { useState } from 'react';
import { Search, Loader2, Mic } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          {isLoading ? (
            <Loader2 className="h-5 w-5 text-orange-500 animate-spin" />
          ) : (
            <Search className="h-5 w-5 text-zinc-400 group-focus-within:text-orange-500 transition-colors" />
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "Can I sell 5 tonnes of tomatoes today?"'
          className="block w-full pl-11 pr-24 py-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none transition-all placeholder:text-zinc-400 text-zinc-900 dark:text-zinc-100 font-medium"
        />
        <div className="absolute inset-y-0 right-24 pr-4 flex items-center">
          <button 
            type="button" 
            className="p-2 text-zinc-400 hover:text-orange-500 transition-colors"
            title="Ask by voice"
          >
            <Mic className="h-5 w-5" />
          </button>
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="absolute right-2 top-2 bottom-2 px-6 bg-orange-500 text-white rounded-xl font-bold text-sm hover:bg-orange-600 active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none"
        >
          Ask AI
        </button>
      </div>
    </form>
  );
};

export default SearchBar;
