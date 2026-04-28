"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface ActionContextType {
  watchlist: string[];
  addToWatchlist: (item: string) => void;
  removeFromWatchlist: (item: string) => void;
  alerts: any[];
  addAlert: (alert: any) => void;
  removeAlert: (id: string) => void;
}

const ActionContext = createContext<ActionContextType | undefined>(undefined);

export function ActionProvider({ children }: { children: ReactNode }) {
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  // Load from local storage on mount
  useEffect(() => {
    const savedWatchlist = localStorage.getItem("mandisense_watchlist");
    const savedAlerts = localStorage.getItem("mandisense_alerts");
    if (savedWatchlist) setWatchlist(JSON.parse(savedWatchlist));
    if (savedAlerts) setAlerts(JSON.parse(savedAlerts));
  }, []);

  const addToWatchlist = (item: string) => {
    if (!watchlist.includes(item)) {
      const updated = [...watchlist, item];
      setWatchlist(updated);
      localStorage.setItem("mandisense_watchlist", JSON.stringify(updated));
    }
  };

  const removeFromWatchlist = (item: string) => {
    const updated = watchlist.filter(w => w !== item);
    setWatchlist(updated);
    localStorage.setItem("mandisense_watchlist", JSON.stringify(updated));
  };

  const addAlert = (alert: any) => {
    const newAlert = { ...alert, id: Date.now().toString(), createdAt: new Date().toISOString(), status: "ACTIVE" };
    const updated = [...alerts, newAlert];
    setAlerts(updated);
    localStorage.setItem("mandisense_alerts", JSON.stringify(updated));
  };

  const removeAlert = (id: string) => {
    const updated = alerts.filter(a => a.id !== id);
    setAlerts(updated);
    localStorage.setItem("mandisense_alerts", JSON.stringify(updated));
  };

  return (
    <ActionContext.Provider value={{ watchlist, addToWatchlist, removeFromWatchlist, alerts, addAlert, removeAlert }}>
      {children}
    </ActionContext.Provider>
  );
}

export function useActionSystem() {
  const context = useContext(ActionContext);
  if (context === undefined) {
    throw new Error("useActionSystem must be used within an ActionProvider");
  }
  return context;
}
