import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export const warnReportAuthor = ({
  reportId,
}: {
  reportId: number;
}): Promise<{ action: string; report_id: number; warned_user_id: number }> => {
  return api.post(`/reports/${reportId}/warn`);
};

export const useWarnReportAuthor = ({
  mutationConfig,
}: { mutationConfig?: MutationConfig<typeof warnReportAuthor> } = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};
  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['admin-reports'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: warnReportAuthor,
  });
};

export const banReportAuthor = ({
  reportId,
}: {
  reportId: number;
}): Promise<{ action: string; report_id: number; banned_user_id: number }> => {
  return api.post(`/reports/${reportId}/ban`);
};

export const useBanReportAuthor = ({
  mutationConfig,
}: { mutationConfig?: MutationConfig<typeof banReportAuthor> } = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};
  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['admin-reports'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: banReportAuthor,
  });
};

export const deleteReportedContent = ({
  reportId,
}: {
  reportId: number;
}): Promise<{
  action: string;
  report_id: number;
  target_type: string;
  target_id: number;
}> => {
  return api.post(`/reports/${reportId}/delete-content`);
};

export const useDeleteReportedContent = ({
  mutationConfig,
}: {
  mutationConfig?: MutationConfig<typeof deleteReportedContent>;
} = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};
  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['admin-reports'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: deleteReportedContent,
  });
};

export const lockReportedDiscussion = ({
  reportId,
}: {
  reportId: number;
}): Promise<{
  action: string;
  report_id: number;
  discussion_id: number;
}> => {
  return api.post(`/reports/${reportId}/lock`);
};

export const useLockReportedDiscussion = ({
  mutationConfig,
}: {
  mutationConfig?: MutationConfig<typeof lockReportedDiscussion>;
} = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};
  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['admin-reports'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: lockReportedDiscussion,
  });
};
