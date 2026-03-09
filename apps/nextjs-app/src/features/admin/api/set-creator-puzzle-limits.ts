import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';

export type SetCreatorPuzzleLimitsDTO = {
  targetUserId: number;
  maxPublished: number;
  maxUnpublished: number;
};

export const setCreatorPuzzleLimits = ({
  targetUserId,
  maxPublished,
  maxUnpublished,
}: SetCreatorPuzzleLimitsDTO) => {
  return api.post('/admin/creator-puzzle-limits', {
    target_user_id: targetUserId,
    max_published: maxPublished,
    max_unpublished: maxUnpublished,
  });
};

type UseSetCreatorPuzzleLimitsOptions = {
  mutationConfig?: MutationConfig<typeof setCreatorPuzzleLimits>;
};

export const useSetCreatorPuzzleLimits = ({
  mutationConfig,
}: UseSetCreatorPuzzleLimitsOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getUsersQueryOptions().queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: setCreatorPuzzleLimits,
  });
};
