import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const voteDiscussion = ({
  discussionId,
  value,
}: {
  discussionId: string;
  value: number;
}): Promise<{
  discussion_id: number;
  user_vote: number | null;
  upvotes: number;
  downvotes: number;
}> => {
  return api.post(`/discussions/${discussionId}/vote`, { value });
};

type UseVoteDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof voteDiscussion>;
};

export const useVoteDiscussion = ({
  discussionId,
  mutationConfig,
}: UseVoteDiscussionOptions) => {
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
    mutationFn: voteDiscussion,
  });
};
