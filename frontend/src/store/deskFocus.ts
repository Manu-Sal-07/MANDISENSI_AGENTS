import { create } from 'zustand';

/**
 * The commodity and mandi the trader tools are focused on. Held in one place so
 * the choice carries from tool to tool as you move between their pages.
 */
interface DeskFocus {
  commodity: string;
  mandiId: string;
  setCommodity: (c: string) => void;
  setMandiId: (m: string) => void;
}

export const useDeskFocus = create<DeskFocus>((set) => ({
  commodity: 'tomato',
  mandiId: 'kolar_apmc',
  setCommodity: (commodity) => set({ commodity }),
  setMandiId: (mandiId) => set({ mandiId }),
}));
