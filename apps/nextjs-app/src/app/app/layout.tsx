import { ReactNode } from 'react';

import AuthGate from './_components/auth-gate';
import { DashboardLayout } from './_components/dashboard-layout';

export const metadata = {
  title: 'Dashboard',
  description: 'Dashboard',
};

const AppLayout = ({ children }: { children: ReactNode }) => {
  return (
    <AuthGate>
      <DashboardLayout>{children}</DashboardLayout>
    </AuthGate>
  );
};

export default AppLayout;
