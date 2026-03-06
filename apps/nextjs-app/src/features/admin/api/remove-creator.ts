import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getUsersQueryOptions } from '@/features/users/api/get-users';

export type RemoveCreatorDTO = {
  targetUserId: number;
};

export type ConfirmRemoveCreatorDTO = {
  targetUserId: number;
  action: 'unpublish' | 'delete' | 'leave';
};

export type RemoveCreatorResponse = {
  ok: boolean;
  user_id?: number;
  username?: string;
  published_count?: number;
  draft_count?: number;
  published_puzzles?: Array<{ id: number; name: string }>;
  admin_action_required?: boolean;
  was_pending?: boolean;
  new_role?: string;
};

export const removeCreator = ({ targetUserId }: RemoveCreatorDTO): Promise<RemoveCreatorResponse> => {
  return api.post('/admin/remove-creator', { target_user_id: targetUserId });
};

export const confirmRemoveCreator = ({ targetUserId, action }: ConfirmRemoveCreatorDTO) => {
  return api.post('/admin/confirm-remove-creator', { target_user_id: targetUserId, action });
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

type UseConfirmRemoveCreatorOptions = {
  mutationConfig?: MutationConfig<typeof confirmRemoveCreator>;
};

export const useConfirmRemoveCreator = ({
  mutationConfig,
}: UseConfirmRemoveCreatorOptions = {}) => {
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
    mutationFn: confirmRemoveCreator,
  });
};
