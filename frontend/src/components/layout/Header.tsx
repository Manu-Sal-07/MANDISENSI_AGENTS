"use client";

import { ArrowLeft, ChevronDown, Bell, Bookmark } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useActionSystem } from "@/context/ActionContext";

export function Header() {
  const { watchlist, alerts } = useActionSystem();

  return (
    <header className="flex-none bg-background/80 backdrop-blur-md border-b border-border z-10 w-full">
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="icon" className="rounded-full">
              <ArrowLeft className="w-5 h-5" />
              <span className="sr-only">Back</span>
            </Button>
          </Link>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">MandiSense AI</span>
            <button className="flex items-center text-lg font-bold tracking-tight text-foreground hover:opacity-80">
              Tomato (Kolar) <ChevronDown className="w-4 h-4 ml-1 opacity-50" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 mr-2">
            <div className="relative cursor-pointer hover:opacity-80">
              <Bookmark className="w-5 h-5 text-muted-foreground" />
              {watchlist.length > 0 && (
                <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white border-2 border-background">
                  {watchlist.length}
                </span>
              )}
            </div>
            <div className="relative cursor-pointer hover:opacity-80">
              <Bell className="w-5 h-5 text-muted-foreground" />
              {alerts.length > 0 && (
                <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-white border-2 border-background">
                  {alerts.length}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center bg-muted/50 p-1 rounded-full border border-border">
            <span className="px-3 py-1 text-xs font-bold bg-primary text-primary-foreground rounded-full">Farmer</span>
            <span className="px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Pro</span>
          </div>
        </div>
      </div>
    </header>
  );
}
