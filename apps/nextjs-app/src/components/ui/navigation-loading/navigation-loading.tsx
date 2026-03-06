'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type NavigationLoadingContextValue = {
  isNavigating: boolean;
  startNavigation: () => void;
};

const NavigationLoadingContext = createContext<NavigationLoadingContextValue | null>(null);

export const NavigationLoadingProvider = ({ children }: { children: React.ReactNode }) => {
  const [isNavigating, setIsNavigating] = useState(false);
  const [navigationStartKey, setNavigationStartKey] = useState<string | null>(null);
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const routeKey = `${pathname}?${searchParams?.toString() ?? ''}`;

  const startNavigation = useCallback(() => {
    setNavigationStartKey(routeKey);
    setIsNavigating(true);
  }, [routeKey]);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const target = event.target as HTMLElement | null;
      const anchor = target?.closest('a');
      if (!anchor) return;

      if (anchor.target === '_blank') return;
      if (anchor.hasAttribute('download')) return;

      const href = anchor.getAttribute('href') ?? '';
      if (!href) return;
      if (href.startsWith('#')) return;
      if (href.startsWith('mailto:') || href.startsWith('tel:')) return;

      if (href.startsWith('http://') || href.startsWith('https://')) {
        const destination = new URL(href, window.location.origin);
        if (destination.origin !== window.location.origin) return;
      }

      startNavigation();
    };

    document.addEventListener('click', handleDocumentClick, true);
    return () => document.removeEventListener('click', handleDocumentClick, true);
  }, [startNavigation]);

  useEffect(() => {
    if (!isNavigating || !navigationStartKey) return;

    // Hide only after we are actually in a different route/search state.
    if (routeKey === navigationStartKey) return;

    const settleTimer = window.setTimeout(() => {
      setIsNavigating(false);
      setNavigationStartKey(null);
    }, 180);

    return () => window.clearTimeout(settleTimer);
  }, [routeKey, isNavigating, navigationStartKey]);

  useEffect(() => {
    if (!isNavigating) return;

    // Safety timeout in case a navigation gets interrupted.
    const failSafeTimer = window.setTimeout(() => {
      setIsNavigating(false);
      setNavigationStartKey(null);
    }, 10000);
    return () => window.clearTimeout(failSafeTimer);
  }, [isNavigating]);

  const value = useMemo(
    () => ({
      isNavigating,
      startNavigation,
    }),
    [isNavigating, startNavigation],
  );

  return (
    <NavigationLoadingContext.Provider value={value}>
      {children}
      {isNavigating && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-[2px]">
          <div className="rounded-xl border border-border bg-card px-6 py-5 shadow-xl">
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:0ms]" />
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:120ms]" />
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:240ms]" />
            </div>
            <p className="mt-3 text-center text-sm text-muted-foreground">Opening page...</p>
          </div>
        </div>
      )}
    </NavigationLoadingContext.Provider>
  );
};

export const useNavigationLoading = () => {
  const context = useContext(NavigationLoadingContext);
  if (!context) {
    throw new Error('useNavigationLoading must be used within NavigationLoadingProvider');
  }
  return context;
};
