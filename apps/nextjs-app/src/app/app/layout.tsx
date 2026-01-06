import { ReactNode } from 'react';

import { DashboardLayout } from './_components/dashboard-layout';

export const metadata = {
  title: 'Dashboard',
  description: 'Dashboard',
};

import { paths } from '@/config/paths';
import { checkLoggedIn } from '@/utils/auth';
import { redirect } from 'next/navigation';

const AppLayout = ({ children }: { children: ReactNode }) => {
  const isLoggedIn = checkLoggedIn();

  if (!isLoggedIn) {
    redirect(paths.auth.login.getHref());
  }

  return <DashboardLayout>{children}</DashboardLayout>;
};

export default AppLayout;
