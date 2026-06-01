'use client';

import { Medal, Trophy } from 'lucide-react';
import { useState } from 'react';

import { InfoPopup } from '@/components/ui/info-popup';
import { useLeaderboard } from '@/features/puzzles/api/get-leaderboard';
import { useUser } from '@/lib/auth';

import {
  formatLeaderboardCost,
  formatLeaderboardTime,
} from '../lib/leaderboard-format';
import { formatFirstSolved } from '../utils/format-first-solved';

const MEDAL_LABELS: Record<number, string> = {
  3: 'Gold',
  2: 'Silver',
  1: 'Bronze',
  0: '',
};

const MEDAL_TINTS: Record<number, string> = {
  3: 'text-amber-500',
  2: 'text-slate-400',
  1: 'text-amber-700',
  0: '',
};

const RANK_STYLES: Record<number, string> = {
  1: 'bg-gradient-to-r from-amber-400 to-yellow-300 text-amber-950 shadow-lg shadow-amber-200/50 scale-[1.02]',
  2: 'bg-gradient-to-r from-slate-300 to-gray-200 text-slate-800 shadow-md shadow-slate-200/50',
  3: 'bg-gradient-to-r from-amber-600 to-orange-400 text-amber-950 shadow-md shadow-orange-200/50',
};

const getMetricDisplay = (
  entry: any,
  type: 'time' | 'cost' | 'first_solved',
) => {
  if (type === 'time') {
    return formatLeaderboardTime(entry.best_time);
  }
  if (type === 'cost') {
    return formatLeaderboardCost(entry.best_cost);
  }
  return formatFirstSolved(entry.first_solved_at);
};

export const PuzzleLeaderboard = ({ puzzleId }: { puzzleId: string }) => {
  const [leaderboardType, setLeaderboardType] = useState<
    'time' | 'cost' | 'first_solved'
  >('time');
  const user = useUser();
  const leaderboardQuery = useLeaderboard({ puzzleId, type: leaderboardType });
  const entries = leaderboardQuery.data?.data ?? [];

  if (leaderboardQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="size-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground" />
      </div>
    );
  }

  const currentUserId = (user.data as any)?.id;

  return (
    <div className="space-y-3">
      {/* Leaderboard Type Tabs */}
      <div className="flex gap-2 border-b border-border">
        <button
          onClick={() => setLeaderboardType('time')}
          className={`rounded px-3 py-2 text-[13px] font-medium transition-colors ${
            leaderboardType === 'time'
              ? 'bg-gray-50 text-black dark:bg-gray-600 dark:text-black'
              : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white'
          }`}
        >
          Fastest Time
        </button>
        <button
          onClick={() => setLeaderboardType('cost')}
          className={`rounded px-3 py-2 text-[13px] font-medium transition-colors ${
            leaderboardType === 'cost'
              ? 'bg-gray-50 text-black dark:bg-gray-600 dark:text-black'
              : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white'
          }`}
        >
          Lowest Cost
        </button>
        <button
          onClick={() => setLeaderboardType('first_solved')}
          className={`rounded px-3 py-2 text-[13px] font-medium transition-colors ${
            leaderboardType === 'first_solved'
              ? 'bg-gray-50 text-black dark:bg-gray-600 dark:text-black'
              : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white'
          }`}
        >
          First Solved
        </button>
      </div>

      {/* Leaderboard Content */}
      {entries.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <Trophy className="size-8 text-muted-foreground/60" aria-hidden />
          <p className="text-sm font-medium text-foreground">No solvers yet!</p>
          <p className="text-xs text-muted-foreground">
            Be the first to solve this puzzle and claim the top spot.
          </p>
        </div>
      ) : (
        <>
          {/* Top 3 podium */}
          {entries.length >= 3 && (
            <div className="mb-4 flex items-end justify-center gap-2 px-2 pt-2">
              {/* 2nd place */}
              <div className="flex w-20 flex-col items-center">
                <div className="mb-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                  2nd
                </div>
                <div className="flex h-16 w-full items-end justify-center rounded-t-lg bg-gradient-to-t from-slate-300 to-slate-200 pb-1">
                  <span className="truncate px-1 text-[10px] font-bold text-slate-700">
                    {entries[1].username}
                  </span>
                </div>
                <div className="w-full rounded-b bg-slate-400/20 px-1 py-0.5 text-center text-[10px] font-semibold tabular-nums text-muted-foreground">
                  {getMetricDisplay(entries[1], leaderboardType)}
                </div>
              </div>
              {/* 1st place */}
              <div className="flex w-24 flex-col items-center">
                <div className="mb-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                  1st
                </div>
                <div className="flex h-24 w-full items-end justify-center rounded-t-lg bg-gradient-to-t from-amber-400 to-yellow-200 pb-1 shadow-lg shadow-amber-200/40">
                  <span className="truncate px-1 text-[11px] font-bold text-amber-900">
                    {entries[0].username}
                  </span>
                </div>
                <div className="w-full rounded-b bg-amber-400/20 px-1 py-0.5 text-center text-[10px] font-bold tabular-nums text-amber-700">
                  {getMetricDisplay(entries[0], leaderboardType)}
                </div>
              </div>
              {/* 3rd place */}
              <div className="flex w-20 flex-col items-center">
                <div className="mb-1 rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-orange-700">
                  3rd
                </div>
                <div className="flex h-12 w-full items-end justify-center rounded-t-lg bg-gradient-to-t from-orange-400 to-amber-200 pb-1">
                  <span className="truncate px-1 text-[10px] font-bold text-orange-900">
                    {entries[2].username}
                  </span>
                </div>
                <div className="w-full rounded-b bg-orange-400/20 px-1 py-0.5 text-center text-[10px] font-semibold tabular-nums text-muted-foreground">
                  {getMetricDisplay(entries[2], leaderboardType)}
                </div>
              </div>
            </div>
          )}

          {/* Full list */}
          <div className="space-y-1">
            {entries.map((entry) => {
              const isCurrentUser =
                currentUserId && entry.user_id === currentUserId;
              const isTopThree = entry.rank <= 3;
              const medalLabel = MEDAL_LABELS[entry.best_medal] ?? '';
              const medalTint = MEDAL_TINTS[entry.best_medal] ?? '';

              return (
                <div
                  key={entry.user_id}
                  className={`flex items-center gap-2.5 rounded-lg px-3 py-2 transition-all ${
                    isTopThree
                      ? RANK_STYLES[entry.rank]
                      : isCurrentUser
                        ? 'border border-blue-300/60 bg-blue-50/50'
                        : 'border border-border/40 bg-card/50 hover:bg-secondary/60'
                  }`}
                >
                  {/* Rank badge */}
                  <div
                    className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      isTopThree
                        ? 'bg-white/40 backdrop-blur-sm'
                        : 'bg-secondary text-muted-foreground'
                    }`}
                  >
                    {entry.rank}
                  </div>

                  {/* Username + medal */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`truncate text-[13px] font-semibold ${
                          isCurrentUser && !isTopThree ? 'text-blue-700' : ''
                        }`}
                      >
                        {entry.username}
                      </span>
                      {isCurrentUser && (
                        <span className="shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-blue-600">
                          You
                        </span>
                      )}
                    </div>
                    {medalLabel && (
                      <div className="mt-0.5 flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Medal className={`size-3 ${medalTint}`} aria-hidden />
                        <span>{medalLabel}</span>
                      </div>
                    )}
                  </div>

                  {/* Metric */}
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-bold tabular-nums">
                      {getMetricDisplay(entry, leaderboardType)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-center gap-1 pt-2 text-[10px] text-muted-foreground/60">
            {leaderboardType === 'time' ? (
              <>
                Ranked by fastest solve time
                <InfoPopup>
                  <p className="mb-1 font-medium text-foreground">
                    Leaderboard & Medals
                  </p>
                  <p>
                    Rank is determined by your{' '}
                    <span className="font-medium text-foreground">
                      fastest solve time
                    </span>{' '}
                    across all attempts.
                  </p>
                  <p className="mt-1">
                    Medals (Gold, Silver, Bronze) are earned based on your{' '}
                    <span className="font-medium text-foreground">
                      solve performance
                    </span>{' '}
                    — staying within time and budget limits — not your
                    leaderboard position.
                  </p>
                </InfoPopup>
              </>
            ) : leaderboardType === 'cost' ? (
              <>
                Ranked by lowest cost solution
                <InfoPopup>
                  <p className="mb-1 font-medium text-foreground">
                    Leaderboard & Medals
                  </p>
                  <p>
                    Rank is determined by your{' '}
                    <span className="font-medium text-foreground">
                      lowest cost solution
                    </span>{' '}
                    across all attempts.
                  </p>
                  <p className="mt-1">
                    Medals (Gold, Silver, Bronze) are earned based on your{' '}
                    <span className="font-medium text-foreground">
                      solve performance
                    </span>{' '}
                    — staying within time and budget limits — not your
                    leaderboard position.
                  </p>
                </InfoPopup>
              </>
            ) : (
              <>
                Ranked by first successful solve
                <InfoPopup>
                  <p className="mb-1 font-medium text-foreground">
                    Leaderboard & Medals
                  </p>
                  <p>
                    Rank is determined by the timestamp of your{' '}
                    <span className="font-medium text-foreground">
                      first successful solve
                    </span>
                    .
                  </p>
                  <p className="mt-1">
                    Medals (Gold, Silver, Bronze) are earned based on your{' '}
                    <span className="font-medium text-foreground">
                      solve performance
                    </span>{' '}
                    — staying within time and budget limits — not your
                    leaderboard position.
                  </p>
                </InfoPopup>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};
