import { useMutation } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export const reportReply = ({
  replyId,
  reason,
  details,
}: {
  replyId: string;
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
  return api.post(`/replies/${replyId}/report`, {
    reason,
    details: details || '',
  });
};

type UseReportReplyOptions = {
  mutationConfig?: MutationConfig<typeof reportReply>;
};

export const useReportReply = ({
  mutationConfig,
}: UseReportReplyOptions = {}) => {
  return useMutation({
    ...mutationConfig,
    mutationFn: reportReply,
  });
};
