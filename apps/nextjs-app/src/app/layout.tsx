import { ReactNode } from 'react';

import { AppProvider } from '@/app/provider';

import '@/styles/globals.css';

export const metadata = {
  title: 'EscapeCircuit',
  description: 'Wire your way out. Create and solve logic-circuit puzzles.',
};

const RootLayout = async ({ children }: { children: ReactNode }) => {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-50">
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
};

export default RootLayout;

// We are not prerendering anything because the app is highly dynamic
// and the data depends on the user so we need to send cookies with each request
export const dynamic = 'force-dynamic';
