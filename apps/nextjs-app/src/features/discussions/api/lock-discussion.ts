import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const lockDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{
  id: number;
  is_locked: boolean;
}> => {
  return api.post(`/discussions/${discussionId}/lock`);
};

type UseLockDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof lockDiscussion>;
};

export const useLockDiscussion = ({
  discussionId,
  mutationConfig,
}: UseLockDiscussionOptions) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getDiscussionQueryOptions(discussionId).queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: lockDiscussion,
  });
};
