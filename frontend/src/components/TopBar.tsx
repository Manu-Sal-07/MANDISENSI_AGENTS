'use client';

import { Activity, Bell, Search, User, Sun, Moon } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { usePathname } from 'next/navigation';
import Link from 'next/link';

export default function TopBar() {
  const { theme, toggleTheme, mounted } = useTheme();
  const pathname = usePathname();

  if (pathname === '/terminal') {
    return null;
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-black/80 backdrop-blur-xl">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <div className="hidden md:flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <Activity className="text-white w-5 h-5" />
            </div>
            <span className="font-bold text-xl tracking-tight text-zinc-900 dark:text-zinc-100">
              MandiSense <span className="text-emerald-600">AI</span>
            </span>
          </Link>
          <div className="hidden lg:flex items-center gap-3">
            <Link href="/market-explorer" className="text-sm font-semibold text-zinc-600 transition hover:text-zinc-900 dark:text-zinc-300">
              Market Explorer
            </Link>
            <Link href="/intelligence-lab" className="text-sm font-semibold text-zinc-600 transition hover:text-zinc-900 dark:text-zinc-300">
              Intelligence Lab
            </Link>
            <Link href="/terminal" className="text-sm font-semibold text-zinc-600 transition hover:text-zinc-900 dark:text-zinc-300">
              Command Center
            </Link>
          </div>
        </div>
        
        <div className="hidden md:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input 
              type="text" 
              placeholder="Search mandi or commodity..." 
              disabled
              className="w-full bg-zinc-100 dark:bg-zinc-900 border-none rounded-full py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-50 cursor-not-allowed"
            />
          </div>
        </div>
        
        <div className="flex items-center gap-2 md:gap-4">
          {/* Theme Toggle - Hydration Safe */}
          <button 
            onClick={toggleTheme}
            className="p-2 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl transition-all active:scale-95 min-w-[40px] flex items-center justify-center"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {!mounted ? (
               <div className="w-5 h-5" /> // Empty space during hydration
            ) : theme === 'dark' ? (
               <Sun className="w-5 h-5" />
            ) : (
               <Moon className="w-5 h-5" />
            )}
          </button>

          <button className="p-2 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white dark:border-black"></span>
          </button>
          
          <div className="w-9 h-9 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center overflow-hidden border border-zinc-200 dark:border-zinc-700">
            <User className="w-5 h-5 text-zinc-400" />
          </div>
        </div>
      </div>
    </header>
  );
}
