import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle, Meta } from '@/types/api';

export const getPuzzles = (
  { page }: { page?: number } = { page: 1 },
): Promise<{
  data: Puzzle[];
  meta: Meta;
}> => {
  return api.get(`/puzzles`, {
    params: {
      page,
      limit: 9,
    },
  });
};

export const getPuzzlesQueryOptions = ({
  page = 1,
}: { page?: number } = {}) => {
  return queryOptions({
    queryKey: ['puzzles', { page }],
    queryFn: () => getPuzzles({ page }),
  });
};

type UsePuzzlesOptions = {
  page?: number;
  config?: QueryConfig<typeof getPuzzlesQueryOptions>;
};

export const usePuzzles = ({ page, config }: UsePuzzlesOptions = {}) => {
  return useQuery({
    ...getPuzzlesQueryOptions({ page }),
    ...config,
  });
};
