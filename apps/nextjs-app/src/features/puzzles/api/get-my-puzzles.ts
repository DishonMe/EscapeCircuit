import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle, Meta } from '@/types/api';

export interface MyPuzzlesFilters {
  page?: number;
  search?: string;
  orderBy?: 'created_at' | 'difficulty' | 'fun' | 'clearness';
  orderDirection?: 'ASC' | 'DESC';
}

export const getMyPuzzles = (
  filters: MyPuzzlesFilters = { page: 1 },
): Promise<{
  data: Puzzle[];
  meta: Meta;
}> => {
  const params: Record<string, any> = {
    page: filters.page || 1,
    limit: 50,
  };

  if (filters.search !== undefined) params.search = filters.search;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;

  return api.get('/puzzles/my-puzzles/list', {
    params,
  });
};

export const myPuzzlesQueryOptions = (filters?: MyPuzzlesFilters) =>
  queryOptions({
    queryKey: ['puzzles', 'my-puzzles', filters],
    queryFn: () => getMyPuzzles(filters),
  });

type UseMyPuzzlesOptions = {
  filters?: MyPuzzlesFilters;
  config?: QueryConfig<typeof getMyPuzzles>;
};

export const useMyPuzzles = ({ filters = {}, config }: UseMyPuzzlesOptions = {}) => {
  return useQuery({
    ...myPuzzlesQueryOptions(filters),
    ...config,
  });
};
