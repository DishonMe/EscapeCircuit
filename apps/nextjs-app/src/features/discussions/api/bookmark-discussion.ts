import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Discussion, Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

export const bookmarkDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{
  discussion_id: number;
  is_bookmarked: boolean;
}> => {
  return api.post(`/discussions/${discussionId}/bookmark`);
};

type UseBookmarkDiscussionOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof bookmarkDiscussion>;
};

export const useBookmarkDiscussion = ({
  discussionId,
  mutationConfig,
}: UseBookmarkDiscussionOptions) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    ...restConfig,
    mutationFn: bookmarkDiscussion,
    onMutate: async () => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<DiscussionWithReplies>(queryKey);

      if (previous?.engagement) {
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...previous,
          engagement: {
            ...previous.engagement,
            is_bookmarked: !previous.engagement.is_bookmarked,
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
            is_bookmarked: data.is_bookmarked,
          },
        });
      }
      onSuccess?.(data, ...rest);
    },
  });
};
