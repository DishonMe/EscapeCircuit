import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Discussion, ThreadCategory } from '@/types/api';

export type DiscussionFilters = {
  limit?: number;
  offset?: number;
  category?: ThreadCategory;
  puzzle_id?: number;
  author_id?: number;
  sort?: 'newest' | 'oldest' | 'most_replies' | 'most_upvotes' | 'trending';
  search?: string;
};

export const getDiscussions = (
  filters: DiscussionFilters = {},
): Promise<{
  discussions: Discussion[];
  total: number;
  limit: number;
  offset: number;
}> => {
  return api.get(`/discussions`, {
    params: {
      limit: filters.limit ?? 20,
      offset: filters.offset ?? 0,
      category: filters.category,
      puzzle_id: filters.puzzle_id,
      author_id: filters.author_id,
      sort: filters.sort ?? 'newest',
      search: filters.search || undefined,
    },
  });
};

export const getDiscussionsQueryOptions = (filters: DiscussionFilters = {}) => {
  return queryOptions({
    queryKey: ['discussions', filters],
    queryFn: () => getDiscussions(filters),
    staleTime: 1000 * 30, // 30s — mutations invalidate on change; avoids re-fetch on rapid navigation
  });
};

type UseDiscussionsOptions = {
  filters?: DiscussionFilters;
  queryConfig?: QueryConfig<typeof getDiscussionsQueryOptions>;
};

export const useDiscussions = ({
  filters = {},
  queryConfig,
}: UseDiscussionsOptions = {}) => {
  return useQuery({
    ...getDiscussionsQueryOptions(filters),
    ...queryConfig,
  });
};
