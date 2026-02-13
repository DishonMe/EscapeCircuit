'use client';

import { useEffect, useRef } from 'react';

import { useCreatorNotifications, useMarkNotificationsRead } from '@/features/notifications/api';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';

/**
 * Fetches unread creator notifications on mount (when user is authenticated).
 * Shows each notification as a toast, then marks them all as read.
 * Renders nothing — pure side-effect component.
 */
const CreatorNotificationsPopup = () => {
  const user = useUser();
  const { data: notifications, status } = useCreatorNotifications();
  const markRead = useMarkNotificationsRead();
  const { addNotification } = useNotifications();
  const shownRef = useRef(false);

  useEffect(() => {
    // Only fire once per mount, only when data is ready, only when we have a user
    if (
      shownRef.current ||
      status !== 'success' ||
      !notifications ||
      notifications.length === 0 ||
      !user.data
    ) {
      return;
    }

    shownRef.current = true;

    // Show each notification as a toast (stagger slightly for UX)
    notifications.forEach((n, i) => {
      setTimeout(() => {
        addNotification({
          type: n.type === 'solve' ? 'success' : 'info',
          title: n.type === 'solve' ? 'Puzzle Solved!' : 'New Rating!',
          message: n.message,
        });
      }, i * 600); // 600ms apart so they don't all pop at once
    });

    // Mark all as read on the server
    markRead.mutate();
  }, [status, notifications, user.data]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
};

export default CreatorNotificationsPopup;
