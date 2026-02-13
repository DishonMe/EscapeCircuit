import { queryOptions, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';

export type CreatorNotification = {
  id: number;
  type: 'solve' | 'rating';
  message: string;
  xp_amount: number;
  puzzle_name: string;
  actor_username: string;
  created_at: string;
};

// --- Fetch unread notifications ---
export const getCreatorNotifications = (): Promise<CreatorNotification[]> => {
  return api.get('/users/me/notifications', {
    suppressErrorNotification: true,
  });
};

export const creatorNotificationsQueryOptions = () =>
  queryOptions({
    queryKey: ['creator-notifications'],
    queryFn: getCreatorNotifications,
    retry: false,
    staleTime: 1000 * 60, // 1 min
  });

export const useCreatorNotifications = () =>
  useQuery(creatorNotificationsQueryOptions());

// --- Mark all as read ---
const markNotificationsRead = (): Promise<{ marked_read: number }> => {
  return api.patch('/users/me/notifications/read');
};

export const useMarkNotificationsRead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: markNotificationsRead,
    onSuccess: () => {
      queryClient.setQueryData(['creator-notifications'], []);
    },
  });
};
