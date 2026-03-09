import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle } from '@/types/api';

export const updatePuzzle = ({
  puzzleId,
  name,
  description,
  instructions,
  creator_comment,
}: {
  puzzleId: string | number;
  name?: string;
  description?: string;
  instructions?: string;
  creator_comment?: string | null;
}): Promise<Puzzle> => {
  const payload: Record<string, any> = {};
  if (name !== undefined) payload.name = name;
  if (description !== undefined) payload.description = description;
  if (instructions !== undefined) payload.instructions = instructions;
  if (creator_comment !== undefined) payload.creator_comment = creator_comment;

  return api.patch(`/puzzles/${puzzleId}`, payload);
};

type UseUpdatePuzzleOptions = {
  config?: QueryConfig<typeof updatePuzzle>;
};

export const useUpdatePuzzle = ({ config }: UseUpdatePuzzleOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePuzzle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      queryClient.invalidateQueries({ queryKey: ['puzzles', 'my-puzzles'] });
    },
    ...config,
  });
};
