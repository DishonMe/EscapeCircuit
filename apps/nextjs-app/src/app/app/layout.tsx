import { ReactNode } from 'react';

import AuthGate from './_components/auth-gate';
import { DashboardLayout } from './_components/dashboard-layout';
import { RedirectNotificationHandler } from './_components/redirect-notification-handler';

export const metadata = {
  title: 'Dashboard',
  description: 'Dashboard',
};

const AppLayout = ({ children }: { children: ReactNode }) => {
  return (
    <AuthGate>
      <RedirectNotificationHandler />
      <DashboardLayout>{children}</DashboardLayout>
    </AuthGate>
  );
};

export default AppLayout;
