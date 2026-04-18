import { queryOptions, useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';

export type LeaderboardEntry = {
  rank: number;
  user_id: number;
  username: string;
  best_time?: number;
  best_cost?: number;
  best_medal: number;
  first_solved_at: string | null;
};

export type LeaderboardResponse = {
  data: LeaderboardEntry[];
};

export const getLeaderboard = ({
  puzzleId,
  type = "time",
}: {
  puzzleId: string;
  type?: "time" | "cost" | "first_solved";
}): Promise<LeaderboardResponse> => {
  return api.get(`/puzzles/${puzzleId}/leaderboard?type=${type}`);
};

export const getLeaderboardQueryOptions = ({
  puzzleId,
  type = "time",
}: {
  puzzleId: string;
  type?: "time" | "cost" | "first_solved";
}) => {
  return queryOptions({
    queryKey: ['leaderboard', { puzzleId, type }],
    queryFn: () => getLeaderboard({ puzzleId, type }),
  });
};

type UseLeaderboardOptions = {
  puzzleId: string;
  type?: "time" | "cost" | "first_solved";
  config?: QueryConfig<typeof getLeaderboardQueryOptions>;
};

export const useLeaderboard = ({ puzzleId, type = "time", config }: UseLeaderboardOptions) => {
  return useQuery({
    ...getLeaderboardQueryOptions({ puzzleId, type }),
    ...config,
  });
};
