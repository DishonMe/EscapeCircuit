import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { AdminAuthAttempt } from '@/types/api';

export type AuthAttemptsFilters = {
  action?: string;
  success?: boolean;
  limit?: number;
  offset?: number;
};

export const getAuthAttempts = (
  filters: AuthAttemptsFilters = {},
): Promise<AdminAuthAttempt[]> => {
  return api.get('/admin/auth-attempts', {
    params: {
      action: filters.action,
      success: filters.success,
      limit: filters.limit ?? 100,
      offset: filters.offset ?? 0,
    },
  });
};

export const getAuthAttemptsQueryOptions = (
  filters: AuthAttemptsFilters = {},
) => {
  return queryOptions({
    queryKey: ['admin-auth-attempts', filters],
    queryFn: () => getAuthAttempts(filters),
  });
};

type UseAuthAttemptsOptions = {
  filters?: AuthAttemptsFilters;
  queryConfig?: QueryConfig<typeof getAuthAttemptsQueryOptions>;
};

export const useAuthAttempts = ({
  filters = {},
  queryConfig,
}: UseAuthAttemptsOptions = {}) => {
  return useQuery({
    ...getAuthAttemptsQueryOptions(filters),
    ...queryConfig,
  });
};
