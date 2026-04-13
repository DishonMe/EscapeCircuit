import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const voteReply = ({
  replyId,
  value,
}: {
  replyId: string;
  value: number;
}): Promise<{
  reply_id: number;
  user_vote: number | null;
  upvotes: number;
  downvotes: number;
}> => {
  return api.post(`/replies/${replyId}/vote`, { value });
};

type UseVoteReplyOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof voteReply>;
};

export const useVoteReply = ({
  discussionId,
  mutationConfig,
}: UseVoteReplyOptions) => {
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
    mutationFn: voteReply,
  });
};
