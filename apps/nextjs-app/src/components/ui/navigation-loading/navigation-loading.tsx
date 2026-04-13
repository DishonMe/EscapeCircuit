'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type NavigationLoadingContextValue = {
  isNavigating: boolean;
  startNavigation: (href?: string) => void;
};

const NavigationLoadingContext = createContext<NavigationLoadingContextValue | null>(null);

export const NavigationLoadingProvider = ({ children }: { children: React.ReactNode }) => {
  const [isNavigating, setIsNavigating] = useState(false);
  const [navigationStartKey, setNavigationStartKey] = useState<string | null>(null);
  const [navigationTargetKey, setNavigationTargetKey] = useState<string | null>(null);
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const routeKey = `${pathname}?${searchParams?.toString() ?? ''}`;

  const keyFromHref = useCallback((href: string): string | null => {
    try {
      const destination = new URL(href, window.location.origin);
      if (destination.origin !== window.location.origin) return null;
      return `${destination.pathname}?${destination.searchParams.toString()}`;
    } catch {
      return null;
    }
  }, []);

  const startNavigation = useCallback((href?: string) => {
    const targetKey = href ? keyFromHref(href) : null;
    // Do not show loader for no-op navigations to current route.
    if (targetKey && targetKey === routeKey) return;

    setNavigationStartKey(routeKey);
    setNavigationTargetKey(targetKey);
    setIsNavigating(true);
  }, [keyFromHref, routeKey]);

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

      startNavigation(href);
    };

    document.addEventListener('click', handleDocumentClick, true);
    return () => document.removeEventListener('click', handleDocumentClick, true);
  }, [startNavigation]);

  useEffect(() => {
    if (!isNavigating || !navigationStartKey) return;

    // Hide only after we are actually in the destination route/search state.
    // If target is unknown (programmatic push), any routeKey change is accepted.
    const reachedDestination = navigationTargetKey
      ? routeKey === navigationTargetKey
      : routeKey !== navigationStartKey;
    if (!reachedDestination) return;

    // Wait for first paint of the new route before hiding the loader.
    let raf1 = 0;
    let raf2 = 0;
    raf1 = window.requestAnimationFrame(() => {
      raf2 = window.requestAnimationFrame(() => {
        setIsNavigating(false);
        setNavigationStartKey(null);
        setNavigationTargetKey(null);
      });
    });

    return () => {
      window.cancelAnimationFrame(raf1);
      window.cancelAnimationFrame(raf2);
    };
  }, [routeKey, isNavigating, navigationStartKey, navigationTargetKey]);

  useEffect(() => {
    if (!isNavigating) return;

    // Safety timeout in case a navigation gets interrupted.
    const failSafeTimer = window.setTimeout(() => {
      setIsNavigating(false);
      setNavigationStartKey(null);
      setNavigationTargetKey(null);
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
