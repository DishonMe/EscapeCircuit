'use client';

import { useState } from 'react';
import { useLeaderboard } from '@/features/puzzles/api/get-leaderboard';
import { useUser } from '@/lib/auth';
import { InfoPopup } from '@/components/ui/info-popup';

const MEDAL_ICONS: Record<number, string> = {
  3: '\u{1F947}', // gold
  2: '\u{1F948}', // silver
  1: '\u{1F949}', // bronze
};

const MEDAL_LABELS: Record<number, string> = {
  3: 'Gold',
  2: 'Silver',
  1: 'Bronze',
  0: '',
};

const RANK_STYLES: Record<number, string> = {
  1: 'bg-gradient-to-r from-amber-400 to-yellow-300 text-amber-950 shadow-lg shadow-amber-200/50 scale-[1.02]',
  2: 'bg-gradient-to-r from-slate-300 to-gray-200 text-slate-800 shadow-md shadow-slate-200/50',
  3: 'bg-gradient-to-r from-amber-600 to-orange-400 text-amber-950 shadow-md shadow-orange-200/50',
};

const formatTime = (seconds: number) => {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${rm}m ${s}s`;
};

const getMetricDisplay = (entry: any, type: "time" | "cost") => {
  if (type === "time") {
    return formatTime(entry.best_time);
  } else {
    return `${entry.best_cost} cost`;
  }
};

export const PuzzleLeaderboard = ({ puzzleId }: { puzzleId: string }) => {
  const [leaderboardType, setLeaderboardType] = useState<"time" | "cost">("time");
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
          onClick={() => setLeaderboardType("time")}
          className={`px-3 py-2 text-[13px] font-medium transition-colors rounded ${
            leaderboardType === "time"
              ? 'text-black dark:text-black bg-gray-50 dark:bg-gray-600'
              : 'text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          ⏱️ Fastest Time
        </button>
        <button
          onClick={() => setLeaderboardType("cost")}
          className={`px-3 py-2 text-[13px] font-medium transition-colors rounded ${
            leaderboardType === "cost"
              ? 'text-black dark:text-black bg-gray-50 dark:bg-gray-600'
              : 'text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          💰 Lowest Cost
        </button>
      </div>

      {/* Leaderboard Content */}
      {entries.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <div className="text-3xl">{'\u{1F3C6}'}</div>
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
            <div className="mb-1 text-xl">{'\u{1F948}'}</div>
            <div className="h-16 w-full rounded-t-lg bg-gradient-to-t from-slate-300 to-slate-200 flex items-end justify-center pb-1">
              <span className="text-[10px] font-bold text-slate-700 truncate px-1">
                {entries[1].username}
              </span>
            </div>
            <div className="w-full rounded-b bg-slate-400/20 px-1 py-0.5 text-center text-[10px] font-semibold text-muted-foreground tabular-nums">
              {getMetricDisplay(entries[1], leaderboardType)}
            </div>
          </div>
          {/* 1st place */}
          <div className="flex w-24 flex-col items-center">
            <div className="mb-1 text-2xl">{'\u{1F947}'}</div>
            <div className="h-24 w-full rounded-t-lg bg-gradient-to-t from-amber-400 to-yellow-200 flex items-end justify-center pb-1 shadow-lg shadow-amber-200/40">
              <span className="text-[11px] font-bold text-amber-900 truncate px-1">
                {entries[0].username}
              </span>
            </div>
            <div className="w-full rounded-b bg-amber-400/20 px-1 py-0.5 text-center text-[10px] font-bold text-amber-700 tabular-nums">
              {getMetricDisplay(entries[0], leaderboardType)}
            </div>
          </div>
          {/* 3rd place */}
          <div className="flex w-20 flex-col items-center">
            <div className="mb-1 text-xl">{'\u{1F949}'}</div>
            <div className="h-12 w-full rounded-t-lg bg-gradient-to-t from-orange-400 to-amber-200 flex items-end justify-center pb-1">
              <span className="text-[10px] font-bold text-orange-900 truncate px-1">
                {entries[2].username}
              </span>
            </div>
            <div className="w-full rounded-b bg-orange-400/20 px-1 py-0.5 text-center text-[10px] font-semibold text-muted-foreground tabular-nums">
              {getMetricDisplay(entries[2], leaderboardType)}
            </div>
          </div>
        </div>
      )}

      {/* Full list */}
      <div className="space-y-1">
        {entries.map((entry) => {
          const isCurrentUser = currentUserId && entry.user_id === currentUserId;
          const isTopThree = entry.rank <= 3;
          const medal = MEDAL_ICONS[entry.best_medal] ?? '';

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
                {medal && (
                  <div className="mt-0.5 flex items-center gap-1 text-[10px] text-muted-foreground">
                    <span>{medal}</span>
                    <span>{MEDAL_LABELS[entry.best_medal]}</span>
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
        {leaderboardType === "time" ? (
          <>
            Ranked by fastest solve time
            <InfoPopup>
              <p className="font-medium text-foreground mb-1">Leaderboard & Medals</p>
              <p>Rank is determined by your <span className="font-medium text-foreground">fastest solve time</span> across all attempts.</p>
              <p className="mt-1">Medals (Gold, Silver, Bronze) are earned based on your <span className="font-medium text-foreground">solve performance</span> — staying within time and budget limits — not your leaderboard position.</p>
            </InfoPopup>
          </>
        ) : (
          <>
            Ranked by lowest cost solution
            <InfoPopup>
              <p className="font-medium text-foreground mb-1">Leaderboard & Medals</p>
              <p>Rank is determined by your <span className="font-medium text-foreground">lowest cost solution</span> across all attempts.</p>
              <p className="mt-1">Medals (Gold, Silver, Bronze) are earned based on your <span className="font-medium text-foreground">solve performance</span> — staying within time and budget limits — not your leaderboard position.</p>
            </InfoPopup>
          </>
        )}
      </div>
        </>
      )}
    </div>
  );
};
