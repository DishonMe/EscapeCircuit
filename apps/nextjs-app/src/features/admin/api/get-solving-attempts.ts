import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { AdminSolvingAttempt } from '@/types/api';

export type SolvingAttemptsFilters = {
  userId?: number;
  puzzleId?: number;
  passed?: boolean;
  limit?: number;
  offset?: number;
};

export type SolvingAttemptsResponse = {
  data: AdminSolvingAttempt[];
  total: number;
  limit: number;
  offset: number;
};

export const getSolvingAttempts = (
  filters: SolvingAttemptsFilters = {},
): Promise<SolvingAttemptsResponse> => {
  return api.get('/admin/solving-attempts', {
    params: {
      user_id: filters.userId,
      puzzle_id: filters.puzzleId,
      passed: filters.passed,
      limit: filters.limit ?? 100,
      offset: filters.offset ?? 0,
    },
  });
};

export const getSolvingAttemptsQueryOptions = (filters: SolvingAttemptsFilters = {}) => {
  return queryOptions({
    queryKey: ['admin-solving-attempts', filters],
    queryFn: () => getSolvingAttempts(filters),
  });
};

type UseSolvingAttemptsOptions = {
  filters?: SolvingAttemptsFilters;
  queryConfig?: QueryConfig<typeof getSolvingAttemptsQueryOptions>;
};

export const useSolvingAttempts = ({ filters = {}, queryConfig }: UseSolvingAttemptsOptions = {}) => {
  return useQuery({
    ...getSolvingAttemptsQueryOptions(filters),
    ...queryConfig,
  });
};
