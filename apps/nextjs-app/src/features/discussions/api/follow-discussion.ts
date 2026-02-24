import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const followDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{
  discussion_id: number;
  is_following: boolean;
}> => {
  return api.post(`/discussions/${discussionId}/follow`);
};

type UseFollowDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof followDiscussion>;
};

export const useFollowDiscussion = ({
  discussionId,
  mutationConfig,
}: UseFollowDiscussionOptions) => {
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
    mutationFn: followDiscussion,
  });
};
