'use client';

import { useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';

import { useUser } from '@/lib/auth';
import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import CreatorNotificationsPopup from '@/features/notifications/creator-notifications-popup';

const AuthGate = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const router = useRouter();
  const pathname = usePathname();
  const { addNotification } = useNotifications();
  const hasShownNotification = useRef(false);

  useEffect(() => {
    // Redirect to login if user query status is no longer pending and either:
    // 1. Query succeeded but returned no user data (no token/session)
    // 2. Query failed with an error (unauthorized - 401)
    if (user.status !== 'pending') {
      const isUnauthenticated = (user.status === 'success' && !user.data) || user.status === 'error';
      if (isUnauthenticated) {
        // Only show notification once to avoid duplicate messages
        if (!hasShownNotification.current) {
          hasShownNotification.current = true;
          addNotification({
            type: 'error',
            title: 'Session Expired',
            message: 'Please log in to continue.',
          });
        }
        router.replace(paths.auth.login.getHref(pathname));
      }
    }
  }, [user.status, user.data, router, pathname, addNotification]);

  return (
    <>
      <CreatorNotificationsPopup />
      {children}
    </>
  );
};

export default AuthGate;
