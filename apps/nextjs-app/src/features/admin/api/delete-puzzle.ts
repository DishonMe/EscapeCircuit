import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export type AdminDeletePuzzleDTO = {
  puzzleId: number;
};

export const adminDeletePuzzle = ({ puzzleId }: AdminDeletePuzzleDTO) => {
  return api.delete(`/admin/puzzles/${puzzleId}`);
};

type UseAdminDeletePuzzleOptions = {
  mutationConfig?: MutationConfig<typeof adminDeletePuzzle>;
};

export const useAdminDeletePuzzle = ({
  mutationConfig,
}: UseAdminDeletePuzzleOptions = {}) => {
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
    mutationFn: adminDeletePuzzle,
  });
};
