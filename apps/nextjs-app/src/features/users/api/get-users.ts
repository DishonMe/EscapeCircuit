import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { User } from '@/types/api';

export interface UserFilters {
  usernameSearch?: string;
  role?: 'ADMIN' | 'CREATOR' | 'SOLVER' | 'admin' | 'creator' | 'solver';
  dateFrom?: string;
  dateTo?: string;
  minLevel?: number;
  maxLevel?: number;
  experienceLevel?: 'all' | 'experienced' | 'inexperienced';
  orderBy?: 'created_at' | 'level' | 'role' | 'experienced';
  orderDirection?: 'ASC' | 'DESC';
  limit?: number;
  offset?: number;
}

export const getUsers = (
  filters: UserFilters = {},
): Promise<{
  data: User[];
  total: number;
  limit: number;
  offset: number;
}> => {
  const params: Record<string, any> = {};

  if (filters.usernameSearch) params.username_search = filters.usernameSearch;
  if (filters.role) params.role = filters.role;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.minLevel !== undefined) params.min_level = filters.minLevel;
  if (filters.maxLevel !== undefined) params.max_level = filters.maxLevel;
  if (filters.experienceLevel)
    params.experience_level = filters.experienceLevel;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;
  if (filters.limit) params.limit = filters.limit;
  if (filters.offset) params.offset = filters.offset;

  return api.get(`/users`, { params });
};

export const getUsersQueryOptions = (filters: UserFilters = {}) => {
  return queryOptions({
    queryKey: ['users', filters],
    queryFn: () => getUsers(filters),
  });
};

type UseUsersOptions = {
  filters?: UserFilters;
  queryConfig?: QueryConfig<typeof getUsersQueryOptions>;
};

export const useUsers = ({
  filters = {},
  queryConfig,
}: UseUsersOptions = {}) => {
  return useQuery({
    ...getUsersQueryOptions(filters),
    ...queryConfig,
  });
};
