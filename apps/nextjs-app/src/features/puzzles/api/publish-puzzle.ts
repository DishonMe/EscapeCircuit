import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle } from '@/types/api';

export const publishPuzzle = (puzzleId: string | number): Promise<Puzzle> => {
  return api.post(`/puzzles/${puzzleId}/publish`, { data: {} });
};

export const unpublishPuzzle = (puzzleId: string | number): Promise<Puzzle> => {
  return api.post(`/puzzles/${puzzleId}/unpublish`, { data: {} });
};

type UsePublishPuzzleOptions = {
  config?: QueryConfig<typeof publishPuzzle>;
};

type UseUnpublishPuzzleOptions = {
  config?: QueryConfig<typeof unpublishPuzzle>;
};

export const usePublishPuzzle = ({ config }: UsePublishPuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: publishPuzzle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      queryClient.invalidateQueries({ queryKey: ['puzzles', 'my-puzzles'] });
    },
    ...config,
  });
};

export const useUnpublishPuzzle = ({
  config,
}: UseUnpublishPuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: unpublishPuzzle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      queryClient.invalidateQueries({ queryKey: ['puzzles', 'my-puzzles'] });
    },
    ...config,
  });
};
