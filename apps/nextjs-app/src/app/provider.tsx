'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import * as React from 'react';
import { ErrorBoundary } from 'react-error-boundary';

import { MainErrorFallback } from '@/components/errors/main';
import { Notifications } from '@/components/ui/notifications';
import { queryConfig } from '@/lib/react-query';
import { enableMocking } from '@/testing/mocks';

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

  const [mswReady, setMswReady] = React.useState(false);

  React.useEffect(() => {
    const init = async () => {
      await enableMocking();
      setMswReady(true);
    };
    init();
  }, []);

  if (!mswReady) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <div className="size-16 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <ErrorBoundary FallbackComponent={MainErrorFallback}>
      <QueryClientProvider client={queryClient}>
        {process.env.DEV && <ReactQueryDevtools />}
        <Notifications />
        {children}
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
