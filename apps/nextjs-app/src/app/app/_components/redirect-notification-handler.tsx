'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';

import { useNotifications } from '@/components/ui/notifications';

/**
 * Displays notifications based on redirect reasons in the query string.
 * Used to inform users why they were redirected.
 */
export const RedirectNotificationHandler = () => {
  const searchParams = useSearchParams();
  const { addNotification } = useNotifications();
  const hasShownRef = useRef(false);

  useEffect(() => {
    if (!hasShownRef.current) {
      const reason = searchParams?.get('reason');

      if (reason === 'already-logged-in') {
        hasShownRef.current = true;
        addNotification({
          type: 'info',
          title: 'Already Logged In',
          message: 'You were redirected because you are already logged in.',
        });
      }
    }
  }, [searchParams, addNotification]);

  return null; // This is a side-effect only component
};
