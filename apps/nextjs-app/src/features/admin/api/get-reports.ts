import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Report } from '@/types/api';

type ReportsResponse = {
  reports: Report[];
  total: number;
  limit: number;
  offset: number;
};

export const getReports = (
  status?: string,
  limit: number = 50,
  offset: number = 0,
): Promise<ReportsResponse> => {
  return api.get('/reports', {
    params: { status: status || undefined, limit, offset },
  });
};

export const getReportsQueryOptions = (status?: string) => {
  return queryOptions({
    queryKey: ['admin-reports', status],
    queryFn: () => getReports(status),
  });
};

type UseReportsOptions = {
  status?: string;
  queryConfig?: QueryConfig<typeof getReportsQueryOptions>;
};

export const useReports = ({ status, queryConfig }: UseReportsOptions = {}) => {
  return useQuery({
    ...getReportsQueryOptions(status),
    ...queryConfig,
  });
};
