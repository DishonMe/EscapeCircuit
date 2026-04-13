import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export type DeleteRatingInput = {
  puzzleId: string;
};

export const deleteRating = ({
  puzzleId,
}: DeleteRatingInput): Promise<{ deleted: boolean }> => {
  return api.delete(`/ratings/puzzle/${puzzleId}`);
};

type UseDeleteRatingOptions = {
  mutationConfig?: MutationConfig<typeof deleteRating>;
};

export const useDeleteRating = ({
  mutationConfig,
}: UseDeleteRatingOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    ...mutationConfig,
    mutationFn: deleteRating,
    onSuccess: (...args) => {
      const input = args[1];
      queryClient.invalidateQueries({
        queryKey: ['puzzle-ratings', { puzzleId: input.puzzleId }],
      });
      queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      mutationConfig?.onSuccess?.(...args);
    },
  });
};
