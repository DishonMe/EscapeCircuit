import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export type AdminUnpublishPuzzleDTO = {
  puzzleId: number;
};

export const adminUnpublishPuzzle = ({
  puzzleId,
}: AdminUnpublishPuzzleDTO): Promise<{ ok: boolean }> => {
  return api.post(`/admin/puzzles/${puzzleId}/unpublish`, {});
};

type UseAdminUnpublishPuzzleOptions = {
  mutationConfig?: MutationConfig<typeof adminUnpublishPuzzle>;
};

export const useAdminUnpublishPuzzle = ({
  mutationConfig,
}: UseAdminUnpublishPuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: ['admin-puzzles'],
      });
      queryClient.invalidateQueries({
        queryKey: ['puzzles'],
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: adminUnpublishPuzzle,
  });
};
