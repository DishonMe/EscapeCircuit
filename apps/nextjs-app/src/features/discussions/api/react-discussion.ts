import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { ReactionCount, ReactionType } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

export const reactToDiscussion = ({
  discussionId,
  reactionType,
}: {
  discussionId: string;
  reactionType: string;
}): Promise<{
  discussion_id: number;
  is_active: boolean;
  reactions: ReactionCount[];
  user_reactions: ReactionType[];
}> => {
  return api.post(`/discussions/${discussionId}/react`, {
    reaction_type: reactionType,
  });
};

type UseReactToDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof reactToDiscussion>;
};

export const useReactToDiscussion = ({
  discussionId,
  mutationConfig,
}: UseReactToDiscussionOptions) => {
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
    mutationFn: reactToDiscussion,
  });
};
