import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Puzzle } from '@/types/api';

type PuzzlesResponse = {
  data: Puzzle[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
};

export const toggleSavePuzzle = ({
  puzzleId,
}: {
  puzzleId: string;
}): Promise<{
  puzzle_id: number;
  is_saved: boolean;
}> => {
  return api.post(`/puzzles/${puzzleId}/save`);
};

type UseToggleSavePuzzleOptions = {
  mutationConfig?: MutationConfig<typeof toggleSavePuzzle>;
};

export const useToggleSavePuzzle = ({
  mutationConfig,
}: UseToggleSavePuzzleOptions) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    ...restConfig,
    mutationFn: toggleSavePuzzle,
    onMutate: async (variables) => {
      const targetPuzzleId = variables.puzzleId;
      // Optimistically update the puzzle list
      await queryClient.cancelQueries({
        queryKey: ['puzzles'],
      });

      const previousData = queryClient.getQueriesData<PuzzlesResponse>({
        queryKey: ['puzzles'],
      });

      // Update all puzzle lists
      queryClient.setQueriesData(
        { queryKey: ['puzzles'] },
        (oldData: PuzzlesResponse | undefined) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            data: oldData.data.map((p) =>
              p.id === targetPuzzleId ? { ...p, is_saved: !p.is_saved } : p,
            ),
          };
        },
      );

      return { previousData };
    },
    onSuccess: (data, variables, onMutateResult, context) => {
      // Invalidate user query to refresh their saved puzzles
      queryClient.invalidateQueries({ queryKey: ['user'] });
      onSuccess?.(data, variables, onMutateResult, context);
    },
    onError: (error, variables, context: any) => {
      // Revert optimistic update on error
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, snapshot]: any) => {
          queryClient.setQueryData(queryKey, snapshot);
        });
      }
    },
  });
};
