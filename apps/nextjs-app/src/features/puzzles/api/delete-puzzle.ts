import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export const deletePuzzle = (puzzleId: string | number): Promise<{ success: boolean }> => {
  return api.delete(`/puzzles/${puzzleId}`);
};

type UseDeletePuzzleOptions = {
  config?: QueryConfig<typeof deletePuzzle>;
};

export const useDeletePuzzle = ({ config }: UseDeletePuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deletePuzzle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      queryClient.invalidateQueries({ queryKey: ['puzzles', 'my-puzzles'] });
    },
    ...config,
  });
};
