import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export type LeaderboardEntry = {
  rank: number;
  user_id: number;
  username: string;
  best_time: number;
  best_medal: number;
  first_solved_at: string | null;
};

export type LeaderboardResponse = {
  data: LeaderboardEntry[];
};

export const getLeaderboard = ({
  puzzleId,
}: {
  puzzleId: string;
}): Promise<LeaderboardResponse> => {
  return api.get(`/puzzles/${puzzleId}/leaderboard`);
};

export const getLeaderboardQueryOptions = ({
  puzzleId,
}: {
  puzzleId: string;
}) => {
  return queryOptions({
    queryKey: ['leaderboard', { puzzleId }],
    queryFn: () => getLeaderboard({ puzzleId }),
  });
};

type UseLeaderboardOptions = {
  puzzleId: string;
  config?: QueryConfig<typeof getLeaderboardQueryOptions>;
};

export const useLeaderboard = ({ puzzleId, config }: UseLeaderboardOptions) => {
  return useQuery({
    ...getLeaderboardQueryOptions({ puzzleId }),
    ...config,
  });
};
