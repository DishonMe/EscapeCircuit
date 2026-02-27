import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

export const acceptReply = ({
  replyId,
}: {
  replyId: string;
}): Promise<Reply> => {
  return api.post(`/replies/${replyId}/accept`);
};

type UseAcceptReplyOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof acceptReply>;
};

export const useAcceptReply = ({
  discussionId,
  mutationConfig,
}: UseAcceptReplyOptions) => {
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
    mutationFn: acceptReply,
  });
};
