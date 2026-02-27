import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Discussion, Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

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
    ...restConfig,
    mutationFn: voteDiscussion,
    onMutate: async ({ value }) => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<DiscussionWithReplies>(queryKey);

      if (previous?.engagement) {
        const eng = previous.engagement;
        const oldVote = eng.user_vote;
        let { upvotes, downvotes } = eng;
        let newVote: number | null = value;

        // Toggle off if same vote
        if (oldVote === value) {
          newVote = null;
          if (value === 1) upvotes--;
          else downvotes--;
        } else {
          // Remove old vote
          if (oldVote === 1) upvotes--;
          else if (oldVote === -1) downvotes--;
          // Add new vote
          if (value === 1) upvotes++;
          else downvotes++;
        }

        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...previous,
          upvotes,
          engagement: { ...eng, upvotes, downvotes, user_vote: newVote },
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
      // Apply server's authoritative values
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      const current = queryClient.getQueryData<DiscussionWithReplies>(queryKey);
      if (current?.engagement) {
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...current,
          upvotes: data.upvotes,
          engagement: {
            ...current.engagement,
            upvotes: data.upvotes,
            downvotes: data.downvotes,
            user_vote: data.user_vote,
          },
        });
      }
      onSuccess?.(data, ...rest);
    },
  });
};
