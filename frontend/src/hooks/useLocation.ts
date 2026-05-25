'use client';

import { useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { logger } from '@/services/logger';

export function useLocation() {
  const { 
    personalizationStatus, 
    setPersonalizationStatus, 
    setUserLocation, 
    setViewMode,
    viewMode
  } = useAppStore();

  const requestLocation = useCallback(async () => {
    // Guard: Only trigger if idle or previously errored, and NOT in manual mode
    if (personalizationStatus === 'requesting' || personalizationStatus === 'granted' || viewMode === 'manual') {
      return;
    }

    if (!navigator.geolocation) {
      setPersonalizationStatus('error');
      logger.logError('Geolocation is not supported by this browser.');
      return;
    }

    setPersonalizationStatus('requesting');
    logger.logInfo('Requesting user location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setUserLocation({ lat: latitude, lon: longitude });
        setPersonalizationStatus('granted');
        setViewMode('personalized');
        logger.logInfo('Location granted', { latitude, longitude });
      },
      (error) => {
        logger.logWarn('Location request failed or denied', { code: error.code, message: error.message });
        
        if (error.code === error.PERMISSION_DENIED) {
          setPersonalizationStatus('denied');
        } else {
          setPersonalizationStatus('error');
        }
        
        // Always fallback to default view on failure. Manual mode returns before requesting location.
        setViewMode('default');
      },
      {
        enableHighAccuracy: false, // Balance speed and precision
        timeout: 10000,
        maximumAge: 3600000, // Cache for 1 hour
      }
    );
  }, [personalizationStatus, setPersonalizationStatus, setUserLocation, setViewMode, viewMode]);

  return { requestLocation, personalizationStatus };
}
