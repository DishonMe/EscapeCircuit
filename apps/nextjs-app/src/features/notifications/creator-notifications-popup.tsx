'use client';

import { useEffect, useRef } from 'react';

import { useCreatorNotifications, useMarkNotificationsRead } from '@/features/notifications/api';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';

const SHOWN_NOTIFICATIONS_KEY = 'escapecircuit_shown_notifications';

/**
 * Fetches unread creator notifications on mount (when user is authenticated).
 * Shows each notification as a toast (won't repeat if already shown).
 * For multiple notifications with no auto-close, shows a "Close All" button.
 * Marks all as read after displaying.
 */
const CREATOR_ROLES = ['creator', 'admin', 'pending_creator'];

const CreatorNotificationsPopup = () => {
  const user = useUser();
  const isCreatorOrAdmin = !!user.data && CREATOR_ROLES.includes(user.data.role);
  const { data: notifications, status } = useCreatorNotifications({
    queryConfig: { enabled: isCreatorOrAdmin },
  });
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

    // Get previously shown notification IDs from localStorage
    const shownNotificationsStr = localStorage.getItem(SHOWN_NOTIFICATIONS_KEY);
    const shownNotifications = shownNotificationsStr ? JSON.parse(shownNotificationsStr) : [];
    const shownSet = new Set(shownNotifications);

    // Filter out already shown notifications
    const newNotifications = notifications.filter((n) => !shownSet.has(n.id));

    if (newNotifications.length === 0) {
      // All notifications have been shown already, just mark as read
      markRead.mutate();
      return;
    }

    // Update localStorage with all current notification IDs
    const allNotificationIds = notifications.map((n) => n.id);
    localStorage.setItem(SHOWN_NOTIFICATIONS_KEY, JSON.stringify(allNotificationIds));

    // Show each notification as a toast (stagger slightly for UX)
    newNotifications.forEach((n, i) => {
      setTimeout(() => {
        let title = 'Notification';
        let type: 'success' | 'info' | 'warning' | 'error' = 'info';
        if (n.type === 'solve') {
          title = 'Puzzle Solved!';
          type = 'success';
        } else if (n.type === 'rating') {
          title = 'New Rating!';
          type = 'info';
        } else if (n.type === 'warning') {
          title = 'Warning';
          type = 'warning';
        } else if (n.type === 'ban') {
          title = 'Account Restriction';
          type = 'error';
        }

        const persistent = n.type === 'warning' || n.type === 'ban';

        addNotification({
          type,
          title,
          message: n.message,
          persistent,
        });
      }, i * 600); // 600ms apart so they don't all pop at once
    });

    // Mark all as read on the server
    markRead.mutate();
  }, [status, notifications, user.data]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
};

export default CreatorNotificationsPopup;
