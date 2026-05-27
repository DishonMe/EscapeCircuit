import { useMutation, useQueryClient } from '@tanstack/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';
import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export type UpdatePuzzleLimitsDTO = {
  userId: number;
  maxPublished: number | null;
  maxUnpublished: number | null;
};

export type UpdatePuzzleLimitsResponse = {
  ok: boolean;
  user_id: number;
  max_published_override: number | null;
  max_unpublished_override: number | null;
  effective_max_published: number;
  effective_max_unpublished: number;
};

export const updatePuzzleLimits = ({
  userId,
  maxPublished,
  maxUnpublished,
}: UpdatePuzzleLimitsDTO): Promise<UpdatePuzzleLimitsResponse> => {
  return api.patch(`/admin/users/${userId}/puzzle-limits`, {
    max_published: maxPublished,
    max_unpublished: maxUnpublished,
  });
};

type UseUpdatePuzzleLimitsOptions = {
  mutationConfig?: MutationConfig<typeof updatePuzzleLimits>;
};

export const useUpdatePuzzleLimits = ({
  mutationConfig,
}: UseUpdatePuzzleLimitsOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getUsersQueryOptions().queryKey,
      });
      queryClient.invalidateQueries({
        queryKey: ['admin-audit-log'],
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: updatePuzzleLimits,
  });
};
