'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

import { useUser } from '@/lib/auth';
import { paths } from '@/config/paths';
import CreatorNotificationsPopup from '@/features/notifications/creator-notifications-popup';

const AuthGate = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (user.status === 'success' && !user.data) {
      router.replace(paths.auth.login.getHref(pathname));
    }
  }, [user.status, user.data, router, pathname]);

  return (
    <>
      <CreatorNotificationsPopup />
      {children}
    </>
  );
};

export default AuthGate;
