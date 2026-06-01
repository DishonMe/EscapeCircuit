import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { AdminPuzzle, Meta } from '@/types/api';

export interface AdminPuzzleFilters {
  page?: number;
  search?: string;
  status?: 'draft' | 'published' | 'unpublished';
  creatorId?: number;
  creatorUsername?: string;
  dateFrom?: string;
  dateTo?: string;
  orderBy?:
    | 'created_at'
    | 'avg_fun'
    | 'avg_clearness'
    | 'rating_count'
    | 'name';
  orderDirection?: 'ASC' | 'DESC';
}

export const getAdminPuzzles = (
  filters: AdminPuzzleFilters = { page: 1 },
): Promise<{ data: AdminPuzzle[]; meta: Meta }> => {
  const params: Record<string, any> = {
    page: filters.page || 1,
    limit: 20,
  };
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.creatorId) params.creator_id = filters.creatorId;
  if (filters.creatorUsername)
    params.creator_username = filters.creatorUsername;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;

  return api.get('/admin/puzzles', { params });
};

export const getAdminPuzzlesQueryOptions = (
  filters: AdminPuzzleFilters = { page: 1 },
) => {
  return queryOptions({
    queryKey: ['admin-puzzles', filters],
    queryFn: () => getAdminPuzzles(filters),
  });
};

type UseAdminPuzzlesOptions = {
  filters?: AdminPuzzleFilters;
  queryConfig?: QueryConfig<typeof getAdminPuzzlesQueryOptions>;
};

export const useAdminPuzzles = ({
  filters = { page: 1 },
  queryConfig,
}: UseAdminPuzzlesOptions = {}) => {
  return useQuery({
    ...getAdminPuzzlesQueryOptions(filters),
    ...queryConfig,
  });
};
