'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { ThemeProvider } from 'next-themes';
import * as React from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { MainErrorFallback } from '@/components/errors/main';
import { NavigationLoadingProvider } from '@/components/ui/navigation-loading/navigation-loading';
import { Notifications } from '@/components/ui/notifications';
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

  return (
    <ErrorBoundary FallbackComponent={MainErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}>
          <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
            <NavigationLoadingProvider>
              {process.env.DEV && <ReactQueryDevtools />}
              <Notifications />
              {children}
            </NavigationLoadingProvider>
          </ThemeProvider>
        </GoogleOAuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
