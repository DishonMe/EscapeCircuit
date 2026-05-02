import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { AdminUserProfile } from '@/types/api';

export const getAdminUserProfile = (userId: number): Promise<AdminUserProfile> => {
  return api.get(`/admin/users/${userId}/profile`);
};

export const getAdminUserProfileQueryOptions = (userId: number) => {
  return queryOptions({
    queryKey: ['admin-user-profile', userId],
    queryFn: () => getAdminUserProfile(userId),
    enabled: Number.isFinite(userId) && userId > 0,
  });
};

type UseAdminUserProfileOptions = {
  userId: number;
  queryConfig?: QueryConfig<typeof getAdminUserProfileQueryOptions>;
};

export const useAdminUserProfile = ({ userId, queryConfig }: UseAdminUserProfileOptions) => {
  return useQuery({
    ...getAdminUserProfileQueryOptions(userId),
    ...queryConfig,
  });
};
