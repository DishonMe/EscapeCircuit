import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { User } from '@/types/api';

export interface UpdatePuzzleLimitsPayload {
  userId: number;
  puzzle_limit_published: number | null;
  puzzle_limit_unpublished: number | null;
}

export const updatePuzzleLimits = ({
  userId,
  puzzle_limit_published,
  puzzle_limit_unpublished,
}: UpdatePuzzleLimitsPayload): Promise<User> => {
  return api.patch(`/users/${userId}/puzzle-limits`, {
    puzzle_limit_published,
    puzzle_limit_unpublished,
  });
};

export const useUpdatePuzzleLimits = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePuzzleLimits,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};
