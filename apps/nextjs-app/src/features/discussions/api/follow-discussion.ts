import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Discussion, Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

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
    ...restConfig,
    mutationFn: followDiscussion,
    onMutate: async () => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<DiscussionWithReplies>(queryKey);

      if (previous?.engagement) {
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...previous,
          engagement: {
            ...previous.engagement,
            is_following: !previous.engagement.is_following,
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
            is_following: data.is_following,
          },
        });
      }
      onSuccess?.(data, ...rest);
    },
  });
};
