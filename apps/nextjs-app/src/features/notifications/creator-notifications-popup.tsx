'use client';

import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';

import { useCreatorNotifications, useMarkNotificationsRead } from '@/features/notifications/api';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';
import { Button } from '@/components/ui/button';

const SHOWN_NOTIFICATIONS_KEY = 'escapecircuit_shown_notifications';

/**
 * Fetches unread creator notifications on mount (when user is authenticated).
 * Shows each notification as a toast (won't repeat if already shown).
 * For multiple notifications with no auto-close, shows a "Close All" button.
 * Marks all as read after displaying.
 */
const CreatorNotificationsPopup = () => {
  const user = useUser();
  const { data: notifications, status } = useCreatorNotifications();
  const markRead = useMarkNotificationsRead();
  const { addNotification } = useNotifications();
  const shownRef = useRef(false);
  const [activeToastIds, setActiveToastIds] = useState<Set<number>>(new Set());

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

    // Track which toasts are currently active
    const toastIds = new Set<number>();

    // Show each notification as a toast (stagger slightly for UX)
    newNotifications.forEach((n, i) => {
      setTimeout(() => {
        toastIds.add(n.id);
        setActiveToastIds(new Set(toastIds));

        const title = n.type === 'solve' ? 'Puzzle Solved!' : 'New Rating!';
        const type = n.type === 'solve' ? 'success' : 'info';

        addNotification({
          type,
          title,
          message: n.message,
          // For multiple notifications, add a close all action hint
          ...(newNotifications.length > 1 && {
            action: (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  // Clear all toasts
                  setActiveToastIds(new Set());
                }}
              >
                <X className="size-4" />
              </Button>
            ),
          }),
        });
      }, i * 600); // 600ms apart so they don't all pop at once
    });

    // Mark all as read on the server
    markRead.mutate();
  }, [status, notifications, user.data]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
};

export default CreatorNotificationsPopup;
