import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { ReactionCount, ReactionType } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

export const reactToReply = ({
  replyId,
  reactionType,
}: {
  replyId: string;
  reactionType: string;
}): Promise<{
  reply_id: number;
  is_active: boolean;
  reactions: ReactionCount[];
  user_reactions: ReactionType[];
}> => {
  return api.post(`/replies/${replyId}/react`, {
    reaction_type: reactionType,
  });
};

type UseReactToReplyOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof reactToReply>;
};

export const useReactToReply = ({
  discussionId,
  mutationConfig,
}: UseReactToReplyOptions) => {
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
    mutationFn: reactToReply,
  });
};
