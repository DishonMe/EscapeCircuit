import { useMutation } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export const reportDiscussion = ({
  discussionId,
  reason,
  details,
}: {
  discussionId: string;
  reason: string;
  details?: string;
}): Promise<{
  id: number;
  reporter_id: number;
  target_type: string;
  target_id: number;
  reason: string;
  details: string;
  status: string;
  created_at: string;
}> => {
  return api.post(`/discussions/${discussionId}/report`, {
    reason,
    details: details || '',
  });
};

type UseReportDiscussionOptions = {
  mutationConfig?: MutationConfig<typeof reportDiscussion>;
};

export const useReportDiscussion = ({
  mutationConfig,
}: UseReportDiscussionOptions = {}) => {
  return useMutation({
    ...mutationConfig,
    mutationFn: reportDiscussion,
  });
};
