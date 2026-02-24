import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

export const createReplyInputSchema = z.object({
  body: z.string().min(1, 'Reply body is required'),
  parent_reply_id: z.number().nullable().optional(),
});

export type CreateReplyInput = z.infer<typeof createReplyInputSchema>;

export const createReply = ({
  data,
  discussionId,
}: {
  data: CreateReplyInput;
  discussionId: string;
}): Promise<Reply> => {
  return api.post(`/discussions/${discussionId}/replies`, data);
};

type UseCreateReplyOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof createReply>;
};

export const useCreateReply = ({
  discussionId,
  mutationConfig,
}: UseCreateReplyOptions) => {
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
    mutationFn: createReply,
  });
};
