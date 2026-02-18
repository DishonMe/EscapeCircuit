'use client';

import { useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Cookies from 'js-cookie';

import { useUser } from '@/lib/auth';
import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';
import CreatorNotificationsPopup from '@/features/notifications/creator-notifications-popup';

const AuthGate = ({ children }: { children: React.ReactNode }) => {
  const user = useUser();
  const router = useRouter();
  const pathname = usePathname();
  const { addNotification } = useNotifications();
  const hasShownNotification = useRef(false);

  useEffect(() => {
    // Only redirect if we're SURE the user is unauthenticated
    // Case 1: User query succeeded but returned no user data (successfully determined no auth)
    // Case 2: User has a valid token but the API returned 401 (unauthorized - session truly expired)
    
    if (user.status === 'success' && !user.data) {
      // Successfully confirmed user is not authenticated
      // Clear the token cookie since it's invalid
      if (Cookies.get(AUTH_TOKEN_COOKIE_NAME)) {
        Cookies.remove(AUTH_TOKEN_COOKIE_NAME);
      }
      
      // Show notification once
      if (!hasShownNotification.current) {
        hasShownNotification.current = true;
        addNotification({
          type: 'error',
          title: 'Session Expired',
          message: 'Please log in to continue.',
        });
      }
      
      // Redirect to login with current page as redirect destination
      router.replace(paths.auth.login.getHref(pathname));
    }
    
    // For errors, we're NOT sure why it failed - could be network, server, etc
    // Don't redirect on errors, just let the page show a loading state
  }, [user.status, user.data, router, pathname, addNotification]);

  return (
    <>
      <CreatorNotificationsPopup />
      {children}
    </>
  );
};

export default AuthGate;
