'use client';

import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from 'next-themes';
import * as React from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { MainErrorFallback } from '@/components/errors/main';
import { NavigationLoadingProvider } from '@/components/ui/navigation-loading/navigation-loading';
import { Notifications } from '@/components/ui/notifications';
import { SettingsProvider } from '@/context/settings-context';
import {
  sweepExpired,
  WORKSTATION_CACHE_VERSION,
  WORKSTATION_KEY_PREFIX,
} from '@/lib/cache-storage';
import { queryConfig } from '@/lib/react-query';

type AppProviderProps = {
  children: React.ReactNode;
};

export const AppProvider = ({ children }: AppProviderProps) => {
  const [queryClient] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: queryConfig,
      }),
  );

  // One-shot cleanup of expired / legacy workstation draft entries on app mount.
  // Silent, best-effort — never throws (SSR-safe inside sweepExpired).
  React.useEffect(() => {
    sweepExpired(WORKSTATION_KEY_PREFIX, WORKSTATION_CACHE_VERSION);
  }, []);

  return (
    <ErrorBoundary FallbackComponent={MainErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <GoogleOAuthProvider
          clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}
        >
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            enableSystem={false}
          >
            <SettingsProvider>
              <NavigationLoadingProvider>
                {process.env.DEV && <ReactQueryDevtools />}
                <Notifications />
                {children}
              </NavigationLoadingProvider>
            </SettingsProvider>
          </ThemeProvider>
        </GoogleOAuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
