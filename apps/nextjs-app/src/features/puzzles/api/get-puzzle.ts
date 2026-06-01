import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle } from '@/types/api';

export const getPuzzle = ({ id }: { id: string }): Promise<Puzzle> => {
  return api.get(`/puzzles/${id}`);
};

export const getPuzzleQueryOptions = ({ id }: { id: string }) => {
  return queryOptions({
    queryKey: ['puzzle', { id }],
    queryFn: () => getPuzzle({ id }),
  });
};

type UsePuzzleOptions = {
  id: string;
  config?: QueryConfig<typeof getPuzzleQueryOptions>;
};

export const usePuzzle = ({ id, config }: UsePuzzleOptions) => {
  return useQuery({
    ...getPuzzleQueryOptions({ id }),
    ...config,
  });
};
