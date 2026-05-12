import { useEffect } from 'react';
import { create } from 'zustand';

const STORAGE_KEY = 'puzzle-instructions-clicked';

type InstructionsGlowStore = {
  hasClicked: boolean;
  hydrated: boolean;
  markClicked: () => void;
  hydrate: () => void;
};

const useStore = create<InstructionsGlowStore>((set, get) => ({
  hasClicked: false,
  hydrated: false,
  markClicked: () => {
    if (get().hasClicked) return;
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(STORAGE_KEY, '1');
      } catch {
        // ignore quota / privacy-mode errors
      }
    }
    set({ hasClicked: true });
  },
  hydrate: () => {
    if (get().hydrated) return;
    let stored = false;
    if (typeof window !== 'undefined') {
      try {
        stored = window.localStorage.getItem(STORAGE_KEY) === '1';
      } catch {
        stored = false;
      }
    }
    set({ hasClicked: stored, hydrated: true });
  },
}));

export const useInstructionsGlow = () => {
  const hasClicked = useStore((s) => s.hasClicked);
  const hydrated = useStore((s) => s.hydrated);
  const markClicked = useStore((s) => s.markClicked);
  const hydrate = useStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return {
    shouldGlow: hydrated && !hasClicked,
    markClicked,
  };
};
