import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Puzzle, Meta } from '@/types/api';

export interface PuzzleFilters {
  page?: number;
  search?: string;
  creator?: string;
  minDifficulty?: number;
  maxDifficulty?: number;
  onlyExperiencedDifficulty?: boolean;
  minClearness?: number;
  maxClearness?: number;
  onlyExperiencedClearness?: boolean;
  minFun?: number;
  maxFun?: number;
  onlyExperiencedFun?: boolean;
  dateFrom?: string;
  dateTo?: string;
  orderBy?: 'created_at' | 'difficulty' | 'fun' | 'clearness';
  orderDirection?: 'ASC' | 'DESC';
  orderOnlyExperienced?: boolean;
  experienceLevel?: 'all' | 'experienced' | 'inexperienced';
  medalFilter?: 'all' | 'unsolved' | 'bronze' | 'silver' | 'gold';
  creator_id?: number;
}

export const getPuzzles = (
  filters: PuzzleFilters = { page: 1 },
): Promise<{
  data: Puzzle[];
  meta: Meta;
}> => {
  const params: Record<string, any> = {
    page: filters.page || 1,
    limit: 9,
  };

  if (filters.search !== undefined) params.search = filters.search;
  if (filters.creator !== undefined) params.creator = filters.creator;
  if (filters.minDifficulty !== undefined) params.min_difficulty = filters.minDifficulty;
  if (filters.maxDifficulty !== undefined) params.max_difficulty = filters.maxDifficulty;
  if (filters.creator_id !== undefined) params.creator_id = filters.creator_id;
  if (filters.experienceLevel === 'experienced') {
    params.only_experienced_difficulty = true;
    params.only_experienced_clearness = true;
    params.only_experienced_fun = true;
    params.order_only_experienced = true;
  } else if (filters.experienceLevel === 'inexperienced') {
    params.only_experienced_difficulty = false;
  }
  if (filters.minClearness !== undefined) params.min_clearness = filters.minClearness;
  if (filters.maxClearness !== undefined) params.max_clearness = filters.maxClearness;
  if (filters.minFun !== undefined) params.min_fun = filters.minFun;
  if (filters.maxFun !== undefined) params.max_fun = filters.maxFun;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.orderBy) params.order_by = filters.orderBy;
  if (filters.orderDirection) params.order_direction = filters.orderDirection;

  return api.get(`/puzzles`, { params });
};

export const getPuzzlesQueryOptions = (
  filters: PuzzleFilters = { page: 1 },
) => {
  return queryOptions({
    queryKey: ['puzzles', filters],
    queryFn: () => getPuzzles(filters),
  });
};

type UsePuzzlesOptions = {
  filters?: PuzzleFilters;
  config?: QueryConfig<typeof getPuzzlesQueryOptions>;
};

export const usePuzzles = ({ filters = { page: 1 }, config }: UsePuzzlesOptions = {}) => {
  return useQuery({
    ...getPuzzlesQueryOptions(filters),
    ...config,
  });
};
