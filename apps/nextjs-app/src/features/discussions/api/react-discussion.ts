import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Discussion, ReactionCount, ReactionType, Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

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
    ...restConfig,
    mutationFn: reactToDiscussion,
    onMutate: async ({ reactionType }) => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<DiscussionWithReplies>(queryKey);

      if (previous?.engagement) {
        const eng = previous.engagement;
        const rt = reactionType as ReactionType;
        const isActive = eng.user_reactions.includes(rt);

        const newUserReactions = isActive
          ? eng.user_reactions.filter((r) => r !== rt)
          : [...eng.user_reactions, rt];

        const newReactions = eng.reactions.map((r) =>
          r.type === rt
            ? { ...r, count: r.count + (isActive ? -1 : 1) }
            : r,
        );
        // Add new reaction type if it wasn't in the list
        if (!isActive && !eng.reactions.some((r) => r.type === rt)) {
          newReactions.push({ type: rt, count: 1 });
        }

        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...previous,
          engagement: {
            ...eng,
            reactions: newReactions.filter((r) => r.count > 0),
            user_reactions: newUserReactions,
          },
        });
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          getDiscussionQueryOptions(discussionId).queryKey,
          context.previous,
        );
      }
    },
    onSuccess: (data, ...rest) => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      const current = queryClient.getQueryData<DiscussionWithReplies>(queryKey);
      if (current?.engagement) {
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...current,
          engagement: {
            ...current.engagement,
            reactions: data.reactions,
            user_reactions: data.user_reactions,
          },
        });
      }
      onSuccess?.(data, ...rest);
    },
  });
};
