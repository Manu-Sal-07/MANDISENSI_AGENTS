import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type PersonalizationStatus = 'idle' | 'requesting' | 'granted' | 'denied' | 'error';
export type ViewMode = 'default' | 'personalized' | 'manual';

interface AppState {
  appStatus: 'initializing' | 'ready' | 'error';
  personalizationStatus: PersonalizationStatus;
  viewMode: ViewMode;
  dataState: any | null;
  userLocation: { lat: number; lon: number } | null;
  selectedMandi: string | null;
  
  // Actions
  setAppStatus: (status: 'initializing' | 'ready' | 'error') => void;
  setPersonalizationStatus: (status: PersonalizationStatus) => void;
  setViewMode: (mode: ViewMode) => void;
  setUserLocation: (location: { lat: number; lon: number } | null) => void;
  setSelectedMandi: (mandiId: string | null) => void;
  
  // High-level Actions
  handleManualMandiSelection: (mandiId: string) => void;
  resetToDefault: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      appStatus: 'initializing',
      personalizationStatus: 'idle',
      viewMode: 'default',
      dataState: null,
      userLocation: null,
      selectedMandi: null,

      setAppStatus: (status) => set({ appStatus: status }),
      setPersonalizationStatus: (status) => set({ personalizationStatus: status }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setUserLocation: (location) => set({ userLocation: location }),
      setSelectedMandi: (mandiId) => set({ selectedMandi: mandiId }),

      handleManualMandiSelection: (mandiId) => set({
        selectedMandi: mandiId,
        viewMode: 'manual'
      }),

      resetToDefault: () => set({
        viewMode: 'default',
        selectedMandi: null,
        personalizationStatus: 'idle',
        userLocation: null
      }),
    }),
    {
      name: 'mandisense-app-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ 
        userLocation: state.userLocation, 
        personalizationStatus: state.personalizationStatus,
        viewMode: state.viewMode,
        selectedMandi: state.selectedMandi
      }),
    }
  )
);
