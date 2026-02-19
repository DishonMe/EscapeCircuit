import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';

export type RemoveCreatorDTO = {
  targetUserId: number;
};

export const removeCreator = ({ targetUserId }: RemoveCreatorDTO) => {
  return api.post('/admin/remove-creator', { target_user_id: targetUserId });
};

type UseRemoveCreatorOptions = {
  mutationConfig?: MutationConfig<typeof removeCreator>;
};

export const useRemoveCreator = ({
  mutationConfig,
}: UseRemoveCreatorOptions = {}) => {
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
    mutationFn: removeCreator,
  });
};
