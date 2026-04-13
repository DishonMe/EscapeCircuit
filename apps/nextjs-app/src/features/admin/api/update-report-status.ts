import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Report } from '@/types/api';

export type UpdateReportStatusDTO = {
  reportId: number;
  status: string;
};

export const updateReportStatus = ({
  reportId,
  status,
}: UpdateReportStatusDTO): Promise<Report> => {
  return api.patch(`/reports/${reportId}`, { status });
};

type UseUpdateReportStatusOptions = {
  mutationConfig?: MutationConfig<typeof updateReportStatus>;
};

export const useUpdateReportStatus = ({
  mutationConfig,
}: UseUpdateReportStatusOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: ['admin-reports'],
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: updateReportStatus,
  });
};
