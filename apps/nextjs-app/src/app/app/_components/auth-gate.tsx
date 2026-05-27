'use client';

import Cookies from 'js-cookie';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useRef } from 'react';

import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import CreatorNotificationsPopup from '@/features/notifications/creator-notifications-popup';
import { useUser } from '@/lib/auth';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

const AuthGate = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const router = useRouter();
  const pathname = usePathname();
  const { addNotification } = useNotifications();
  const hasShownNotification = useRef(false);

  const hasToken = !!Cookies.get(AUTH_TOKEN_COOKIE_NAME);

  useEffect(() => {
    // No cookie at all → redirect immediately without waiting for API
    if (!hasToken) {
      router.replace(paths.auth.login.getHref(pathname));
      return;
    }

    // Cookie exists but API confirmed not authenticated (expired session)
    if (user.status === 'success' && !user.data) {
      Cookies.remove(AUTH_TOKEN_COOKIE_NAME);

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
  }, [user.status, user.data, router, pathname, addNotification, hasToken]);

  return (
    <>
      <CreatorNotificationsPopup />
      {children}
    </>
  );
};

export default AuthGate;
