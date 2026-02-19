import { queryOptions, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export type CreatorNotification = {
  id: number;
  type: 'solve' | 'rating';
  message: string;
  xp_amount: number;
  puzzle_name: string;
  actor_username: string;
  created_at: string;
};

export interface NotificationFilters {
  notifType?: 'solve' | 'rating';
  puzzleName?: string;
  actorUsername?: string;
  dateFrom?: string;
  dateTo?: string;
  orderBy?: 'created_at' | 'xp_amount';
  orderDirection?: 'ASC' | 'DESC';
  limit?: number;
  offset?: number;
}

// --- Fetch unread notifications ---
export const getCreatorNotifications = (filters: NotificationFilters = {}): Promise<CreatorNotification[]> => {
  const params: Record<string, any> = {};
  
  if (filters.notifType) params.notif_type = filters.notifType;
  if (filters.puzzleName) params.puzzle_name = filters.puzzleName;
  if (filters.actorUsername) params.actor_username = filters.actorUsername;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;
  if (filters.limit) params.limit = filters.limit;
  if (filters.offset) params.offset = filters.offset;

  return api.get('/users/me/notifications', {
    params,
    suppressErrorNotification: true,
  });
};

export const creatorNotificationsQueryOptions = (filters: NotificationFilters = {}) =>
  queryOptions({
    queryKey: ['creator-notifications', filters],
    queryFn: () => getCreatorNotifications(filters),
    retry: false,
    staleTime: 1000 * 60, // 1 min
  });

type UseCreatorNotificationsOptions = {
  filters?: NotificationFilters;
  queryConfig?: QueryConfig<typeof creatorNotificationsQueryOptions>;
};

export const useCreatorNotifications = ({ filters = {}, queryConfig }: UseCreatorNotificationsOptions = {}) =>
  useQuery({
    ...creatorNotificationsQueryOptions(filters),
    ...queryConfig,
  });

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

// --- Fetch all notifications history (both read and unread) ---
export const getCreatorNotificationsHistory = async (filters: NotificationFilters = {}): Promise<CreatorNotification[]> => {
  const params: Record<string, any> = {};
  
  if (filters.notifType) params.notif_type = filters.notifType;
  if (filters.puzzleName) params.puzzle_name = filters.puzzleName;
  if (filters.actorUsername) params.actor_username = filters.actorUsername;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;
  if (filters.limit) params.limit = filters.limit;
  if (filters.offset) params.offset = filters.offset;

  return await api.get('/users/me/notifications/history', { params }) as CreatorNotification[];
};

export const creatorNotificationsHistoryQueryOptions = (filters: NotificationFilters = {}) =>
  queryOptions({
    queryKey: ['creator-notifications-history', filters],
    queryFn: () => getCreatorNotificationsHistory(filters),
    retry: 1,
    staleTime: 0, // Always fetch fresh data
  });

type UseCreatorNotificationsHistoryOptions = {
  filters?: NotificationFilters;
  queryConfig?: QueryConfig<typeof creatorNotificationsHistoryQueryOptions>;
};

export const useCreatorNotificationsHistory = ({ filters = {}, queryConfig }: UseCreatorNotificationsHistoryOptions = {}) => 
  useQuery({
    ...creatorNotificationsHistoryQueryOptions(filters),
    ...queryConfig,
  });
