import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { PuzzleRatingsResponse } from '@/types/api';

export const getPuzzleRatings = ({
  puzzleId,
}: {
  puzzleId: string;
}): Promise<PuzzleRatingsResponse> => {
  return api.get(`/ratings/puzzle/${puzzleId}`);
};

export const getPuzzleRatingsQueryOptions = ({
  puzzleId,
}: {
  puzzleId: string;
}) => {
  return queryOptions({
    queryKey: ['puzzle-ratings', { puzzleId }],
    queryFn: () => getPuzzleRatings({ puzzleId }),
  });
};

type UsePuzzleRatingsOptions = {
  puzzleId: string;
  config?: QueryConfig<typeof getPuzzleRatingsQueryOptions>;
};

export const usePuzzleRatings = ({
  puzzleId,
  config,
}: UsePuzzleRatingsOptions) => {
  return useQuery({
    ...getPuzzleRatingsQueryOptions({ puzzleId }),
    ...config,
  });
};
