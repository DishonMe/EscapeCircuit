import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

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
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getDiscussionQueryOptions(discussionId).queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: bookmarkDiscussion,
  });
};
