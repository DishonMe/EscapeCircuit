import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { RatingEntry } from '@/types/api';

export type RatePuzzleInput = {
  puzzleId: string;
  difficulty: number;
  fun: number;
  clearness: number;
  elapsed_seconds?: number;
  mode?: 'create' | 'update';
};

export const ratePuzzle = ({
  puzzleId,
  difficulty,
  fun,
  clearness,
  elapsed_seconds,
  mode = 'create',
}: RatePuzzleInput): Promise<RatingEntry> => {
  const method = mode === 'update' ? api.put : api.post;
  return method(`/ratings/puzzle/${puzzleId}`, {
    difficulty,
    fun,
    clearness,
    elapsed_seconds,
  });
};

type UseRatePuzzleOptions = {
  mutationConfig?: MutationConfig<typeof ratePuzzle>;
};

export const useRatePuzzle = ({
  mutationConfig,
}: UseRatePuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    ...mutationConfig,
    mutationFn: ratePuzzle,
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
