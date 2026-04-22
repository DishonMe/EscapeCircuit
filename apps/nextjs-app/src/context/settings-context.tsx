'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface SettingsContextType {
  soundEnabled: boolean;
  setSoundEnabled: (enabled: boolean) => void;
  visualEffectsEnabled: boolean;
  setVisualEffectsEnabled: (enabled: boolean) => void;
  colabPetsEnabled: boolean;
  setColabPetsEnabled: (enabled: boolean) => void;
  soundVolume: number;
  setSoundVolume: (volume: number) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const STORAGE_KEY = 'escapecircuit-settings';

interface StoredSettings {
  soundEnabled?: boolean;
  visualEffectsEnabled?: boolean;
  colabPetsEnabled?: boolean;
  soundVolume?: number;
}

export const SettingsProvider = ({ children }: { children: React.ReactNode }) => {
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [visualEffectsEnabled, setVisualEffectsEnabled] = useState(true);
  const [colabPetsEnabled, setColabPetsEnabled] = useState(false);
  const [soundVolume, setSoundVolume] = useState(0.6);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const settings: StoredSettings = JSON.parse(stored);
        if (settings.soundEnabled !== undefined) setSoundEnabled(settings.soundEnabled);
        if (settings.visualEffectsEnabled !== undefined) setVisualEffectsEnabled(settings.visualEffectsEnabled);
        if (settings.colabPetsEnabled !== undefined) setColabPetsEnabled(settings.colabPetsEnabled);
        if (settings.soundVolume !== undefined) setSoundVolume(settings.soundVolume);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setIsHydrated(true);
    }
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    if (!isHydrated) return;
    
    try {
      const settings: StoredSettings = {
        soundEnabled,
        visualEffectsEnabled,
        colabPetsEnabled,
        soundVolume,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }, [soundEnabled, visualEffectsEnabled, colabPetsEnabled, soundVolume, isHydrated]);

  const value: SettingsContextType = {
    soundEnabled,
    setSoundEnabled,
    visualEffectsEnabled,
    setVisualEffectsEnabled,
    colabPetsEnabled,
    setColabPetsEnabled,
    soundVolume,
    setSoundVolume,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};
