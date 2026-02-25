import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const pinDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{
  id: number;
  is_pinned: boolean;
}> => {
  return api.post(`/discussions/${discussionId}/pin`);
};

type UsePinDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof pinDiscussion>;
};

export const usePinDiscussion = ({
  discussionId,
  mutationConfig,
}: UsePinDiscussionOptions) => {
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
    mutationFn: pinDiscussion,
  });
};
