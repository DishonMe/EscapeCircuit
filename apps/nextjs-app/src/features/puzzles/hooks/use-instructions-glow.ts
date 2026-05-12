import { useCallback, useEffect, useMemo } from 'react';
import { create } from 'zustand';

import { useUser } from '@/lib/auth';

const STORAGE_PREFIX = 'puzzle-instructions-clicked:';

type InstructionsGlowStore = {
  clickedByKey: Record<string, boolean>;
  hydratedKeys: Record<string, boolean>;
  markClicked: (key: string) => void;
  hydrate: (key: string) => void;
};

const useStore = create<InstructionsGlowStore>((set, get) => ({
  clickedByKey: {},
  hydratedKeys: {},
  markClicked: (key) => {
    if (get().clickedByKey[key]) return;
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(key, '1');
      } catch {
        // ignore quota / privacy-mode errors
      }
    }
    set((s) => ({
      clickedByKey: { ...s.clickedByKey, [key]: true },
    }));
  },
  hydrate: (key) => {
    if (get().hydratedKeys[key]) return;
    let stored = false;
    if (typeof window !== 'undefined') {
      try {
        stored = window.localStorage.getItem(key) === '1';
      } catch {
        stored = false;
      }
    }
    set((s) => ({
      clickedByKey: { ...s.clickedByKey, [key]: stored },
      hydratedKeys: { ...s.hydratedKeys, [key]: true },
    }));
  },
}));

export const useInstructionsGlow = () => {
  const user = useUser();
  const username = user.data?.username;
  const key = useMemo(
    () => (username ? `${STORAGE_PREFIX}${username}` : null),
    [username],
  );

  const hasClicked = useStore((s) => (key ? !!s.clickedByKey[key] : false));
  const hydrated = useStore((s) => (key ? !!s.hydratedKeys[key] : false));
  const markClickedFn = useStore((s) => s.markClicked);
  const hydrateFn = useStore((s) => s.hydrate);

  useEffect(() => {
    if (key) hydrateFn(key);
  }, [key, hydrateFn]);

  const markClicked = useCallback(() => {
    if (key) markClickedFn(key);
  }, [key, markClickedFn]);

  return {
    shouldGlow: !!key && hydrated && !hasClicked,
    markClicked,
  };
};
