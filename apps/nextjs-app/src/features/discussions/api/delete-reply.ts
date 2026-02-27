import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

import { getDiscussionQueryOptions } from './get-discussion';

export const deleteReply = ({ replyId }: { replyId: string }) => {
  return api.delete(`/replies/${replyId}`);
};

type UseDeleteReplyOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof deleteReply>;
};

export const useDeleteReply = ({
  discussionId,
  mutationConfig,
}: UseDeleteReplyOptions) => {
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
    mutationFn: deleteReply,
  });
};
