import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { AuditLogEntry } from '@/types/api';

export const getAuditLog = (
  limit: number = 100,
): Promise<AuditLogEntry[]> => {
  return api.get('/admin/audit-log', { params: { limit } });
};

export const getAuditLogQueryOptions = (limit: number = 100) => {
  return queryOptions({
    queryKey: ['admin-audit-log', limit],
    queryFn: () => getAuditLog(limit),
    staleTime: 0,
    refetchOnMount: 'always',
  });
};

type UseAuditLogOptions = {
  limit?: number;
  queryConfig?: QueryConfig<typeof getAuditLogQueryOptions>;
};

export const useAuditLog = ({
  limit = 100,
  queryConfig,
}: UseAuditLogOptions = {}) => {
  return useQuery({
    ...getAuditLogQueryOptions(limit),
    ...queryConfig,
  });
};
