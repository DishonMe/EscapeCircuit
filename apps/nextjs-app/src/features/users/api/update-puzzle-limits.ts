import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getUsersQueryOptions } from './get-users';

export type UpdatePuzzleLimitsDTO = {
  userId: string;
  maxPublished: number | null;
  maxUnpublished: number | null;
};

export const updatePuzzleLimits = ({
  userId,
  maxPublished,
  maxUnpublished,
}: UpdatePuzzleLimitsDTO) => {
  return api.patch(`/users/${userId}/puzzle-limits`, {
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
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: updatePuzzleLimits,
  });
};
