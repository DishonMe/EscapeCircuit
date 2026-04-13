import {
  dehydrate,
  HydrationBoundary,
  QueryClient,
} from '@tanstack/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';
import { AdminPanel } from './admin-panel';

export const Users = async () => {
  const queryClient = new QueryClient();

  await queryClient.prefetchQuery(getUsersQueryOptions());

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrationBoundary state={dehydratedState}>
      <AdminPanel />
    </HydrationBoundary>
  );
};
