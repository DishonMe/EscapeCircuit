import { useMutation, useQueryClient } from '@tanstack/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';
import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export type AssignCreatorDTO = {
  targetUserId: number;
};

export const assignCreator = ({ targetUserId }: AssignCreatorDTO) => {
  return api.post('/admin/assign-creator', { target_user_id: targetUserId });
};

type UseAssignCreatorOptions = {
  mutationConfig?: MutationConfig<typeof assignCreator>;
};

export const useAssignCreator = ({
  mutationConfig,
}: UseAssignCreatorOptions = {}) => {
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
    mutationFn: assignCreator,
  });
};
