'use client';

import { useState, useEffect } from 'react';

export type ViewMode = 'gallery' | 'list';

const STORAGE_KEY = 'escapecircuit:puzzles-view';
const SM_BREAKPOINT = '(min-width: 640px)';

function readStoredView(): ViewMode {
  if (typeof window === 'undefined') return 'gallery';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'gallery' || stored === 'list') return stored;
  } catch {
    // ignore localStorage errors
  }
  return 'gallery';
}

function isSm(): boolean {
  if (typeof window === 'undefined') return true;
  return window.matchMedia(SM_BREAKPOINT).matches;
}

export function useViewMode(): [ViewMode, (v: ViewMode) => void] {
  // SSR-safe: always start with 'gallery' on server
  const [view, setViewState] = useState<ViewMode>('gallery');

  // After mount: hydrate from localStorage and listen to breakpoint
  useEffect(() => {
    const stored = readStoredView();
    const wide = isSm();
    setViewState(wide ? stored : 'gallery');

    const mq = window.matchMedia(SM_BREAKPOINT);
    const handler = (e: MediaQueryListEvent) => {
      if (!e.matches) {
        // Viewport shrunk below sm — force gallery
        setViewState('gallery');
      } else {
        // Viewport grew — restore stored preference
        setViewState(readStoredView());
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const setView = (v: ViewMode) => {
    setViewState(v);
    try {
      window.localStorage.setItem(STORAGE_KEY, v);
    } catch {
      // ignore localStorage errors
    }
  };

  return [view, setView];
}
