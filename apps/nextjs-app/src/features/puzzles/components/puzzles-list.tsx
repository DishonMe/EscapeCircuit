'use client';

import {
  Clock,
  Star,
  Circle,
  Users,
  Info,
  MessageSquare,
  Medal,
  CheckCircle2,
  Filter,
  X,
  Bookmark,
  Trophy,
} from 'lucide-react';
import { useMemo, useState, ChangeEvent, useEffect } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Link } from '@/components/ui/link';
import { PuzzleXPBar } from '@/components/ui/puzzle-xp-bar';
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';
import { RatingDialog } from '@/features/ratings/components/rating-dialog';

import { usePuzzles, PuzzleFilters } from '../api/get-puzzles';
import { useToggleSavePuzzle } from '../api/save-puzzle';
import { CreatorCommentDialog } from './creator-comment-dialog';
import { PuzzleDetailsDialog } from './puzzle-details-dialog';
import { PuzzleLeaderboard } from './puzzle-leaderboard';
import { cn } from '@/utils/cn';

function useDebouncedValue<T>(value: T, delay: number = 400): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export const PuzzlesList = () => {
  const [detailsPuzzleId, setDetailsPuzzleId] = useState<string | null>(null);
  const [commentPuzzleId, setCommentPuzzleId] = useState<string | null>(null);
  const [leaderboardPuzzleId, setLeaderboardPuzzleId] = useState<string | null>(null);
  const [ratingPuzzleId, setRatingPuzzleId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(true);
  const [filters, setFilters] = useState<PuzzleFilters>({ page: 1 });
  const [creatorSearchInput, setCreatorSearchInput] = useState('');
  const debouncedCreatorSearch = useDebouncedValue(creatorSearchInput, 400);

  useEffect(() => {
    setFilters((prev) => {
      const nextCreator = debouncedCreatorSearch.trim() || undefined;
      if (prev.creator === nextCreator) {
        return prev;
      }

      return {
        ...prev,
        creator: nextCreator,
        page: 1,
      };
    });
  }, [debouncedCreatorSearch]);

  const puzzlesQuery = usePuzzles({
    filters: {
      page: filters.page || 1,
      ...filters,
    },
    config: {
      // Keep prior page/filter results visible while the next request is in-flight.
      placeholderData: (previousData) => previousData,
    },
  });

  const puzzles = puzzlesQuery.data?.data;
  const meta = puzzlesQuery.data?.meta;
  const isRefetching = puzzlesQuery.isFetching && !puzzlesQuery.isLoading;
  const isBusyLoading = puzzlesQuery.isLoading || isRefetching;
  const saveMutation = useToggleSavePuzzle({});

  // Filter puzzles based on medal filter (client-side, based on best_medal)
  const filteredPuzzles = useMemo(() => {
    if (!puzzles) return puzzles;
    if (filters.medalFilter && filters.medalFilter !== 'all') {
      return puzzles.filter((p) => {
        const medal = p.best_medal ?? 0;
        switch (filters.medalFilter) {
          case 'unsolved':
            return medal === 0 || !p.is_solved;
          case 'bronze':
            return medal === 1;
          case 'silver':
            return medal === 2;
          case 'gold':
            return medal === 3;
          default:
            return true;
        }
      });
    }
    return puzzles;
  }, [puzzles, filters.medalFilter]);

  const selectedPuzzle: Puzzle | undefined = useMemo(() => {
    if (!detailsPuzzleId || !puzzles) return undefined;
    return puzzles.find((p) => p.id === detailsPuzzleId);
  }, [detailsPuzzleId, puzzles]);

  const selectedCommentPuzzle: Puzzle | undefined = useMemo(() => {
    if (!commentPuzzleId || !puzzles) return undefined;
    return puzzles.find((p) => p.id === commentPuzzleId);
  }, [commentPuzzleId, puzzles]);

  const selectedLeaderboardPuzzle: Puzzle | undefined = useMemo(() => {
    if (!leaderboardPuzzleId || !puzzles) return undefined;
    return puzzles.find((p) => p.id === leaderboardPuzzleId);
  }, [leaderboardPuzzleId, puzzles]);

  const isEmpty = !filteredPuzzles || filteredPuzzles.length === 0;

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'text-emerald-600 bg-emerald-50 border-emerald-200/60';
      case 'medium':
        return 'text-amber-600 bg-amber-50 border-amber-200/60';
      case 'hard':
        return 'text-red-600 bg-red-50 border-red-200/60';
      default:
        return 'text-muted-foreground bg-secondary border-border';
    }
  };

  const renderStars = (rating: number) => {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <Star
          key={i}
          className={`size-3.5 ${i <= Math.floor(rating)
              ? 'fill-yellow-500 text-yellow-500'
              : 'text-muted-foreground/40'
            }`}
        />,
      );
    }
    return stars;
  };

  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      <div className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className="gap-2"
        >
          <Filter className="size-4" />
          Filters {Object.values(filters).filter((v) => v && v !== 1).length > 0 && `(${Object.values(filters).filter((v) => v && v !== 1).length})`}
        </Button>
        {Object.values(filters).filter((v) => v && v !== 1).length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setFilters({ page: 1 });
              setCreatorSearchInput('');
            }}
            className="text-muted-foreground text-[13px]"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-5">
          {/* Top Level: name, creator, min difficulty, min fun, min clearness */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Search Name */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Search Name</label>
              <input
                type="text"
                placeholder="Puzzle name..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.search || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, search: e.target.value || undefined, page: 1 })}
              />
            </div>

            {/* Search Creator */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Search Creator</label>
              <input
                type="text"
                placeholder="Search by Creator..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={creatorSearchInput}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setCreatorSearchInput(e.target.value)}
              />
            </div>

            {/* Min Difficulty */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Min Difficulty</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.minDifficulty || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, minDifficulty: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              >
                <option value="">Any</option>
                <option value="1">Easy</option>
                <option value="2">Medium</option>
                <option value="3">Hard</option>
              </select>
            </div>

            {/* Min Fun */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Min Fun Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.minFun || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, minFun: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>

            {/* Min Clearness */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Min Clearness Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.minClearness || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, minClearness: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>
          </div>

          {/* Mid Level: order, max difficulty, max fun, max clearness */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Order By */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Order By</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any, page: 1 })}
              >
                <option value="created_at">Newest</option>
                <option value="difficulty">Difficulty</option>
                <option value="fun">Fun</option>
                <option value="clearness">Clearness</option>
              </select>
            </div>

            {/* Max Difficulty */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Max Difficulty</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.maxDifficulty || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, maxDifficulty: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              >
                <option value="">Any</option>
                <option value="1">Easy</option>
                <option value="2">Medium</option>
                <option value="3">Hard</option>
              </select>
            </div>

            {/* Max Fun */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Max Fun Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.maxFun || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, maxFun: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>

            {/* Max Clearness */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Max Clearness Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.maxClearness || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, maxClearness: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>
          </div>

          {/* Last Level: direction, experienced/inexperienced/all, and medal filter */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Direction */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Direction</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderDirection || 'ASC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderDirection: e.target.value as any, page: 1 })}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
              </select>
            </div>

            {/* Experience Level */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Experience Level</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.experienceLevel || 'all'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, experienceLevel: e.target.value as any, page: 1 })}
              >
                <option value="all">All</option>
                <option value="experienced">Experienced</option>
                <option value="inexperienced">Inexperienced</option>
              </select>
            </div>

            {/* Medal Filter */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Medal</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.medalFilter || 'all'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, medalFilter: e.target.value as any, page: 1 })}
              >
                <option value="all">All Puzzles</option>
                <option value="unsolved">Unsolved</option>
                <option value="bronze">Bronze 🥉</option>
                <option value="silver">Silver 🥈</option>
                <option value="gold">Gold 🥇</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Loading popup */}
      {isBusyLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-[2px]">
          <div className="rounded-xl border border-border bg-card px-6 py-5 shadow-xl">
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:0ms]" />
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:120ms]" />
              <span className="size-2 rounded-full bg-foreground animate-bounce [animation-delay:240ms]" />
            </div>
            <p className="mt-3 text-center text-sm text-muted-foreground">Loading page...</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!puzzlesQuery.isLoading && isEmpty && (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-muted-foreground">
          No puzzles available.
        </div>
      )}

      {/* Puzzle Grid */}
      {!puzzlesQuery.isLoading && !isEmpty && (
        <div className="relative">
          <div className={`grid grid-cols-1 gap-6 transition-opacity md:grid-cols-2 lg:grid-cols-3 ${isRefetching ? 'opacity-50' : 'opacity-100'}`}>
          {filteredPuzzles!.map((puzzle) => {
            return (
            <div
              key={puzzle.id}
              className={`relative cursor-pointer rounded-xl border bg-card p-5 transition-all hover:shadow-card ${
                puzzle.is_solved
                  ? 'border-emerald-200/60 hover:border-emerald-300/60'
                  : 'border-border hover:border-foreground/20'
              }`}
            >
            {/* Solved checkmark overlay */}
            {puzzle.is_solved && (
              <div className="absolute -right-2 -top-2 z-10 flex size-7 items-center justify-center rounded-full bg-emerald-500 text-white shadow-md">
                <CheckCircle2 className="size-5" />
              </div>
            )}

          {/* Title & Creator with status badge */}
            <div className="mb-3 flex flex-wrap items-start gap-2">
              <div className="flex-1">
                <h3 className="mb-1 text-[15px] font-medium text-foreground">{puzzle.title}</h3>
                <p className="text-[13px] text-muted-foreground">
                  by{' '}
                  {puzzle.creator ? puzzle.creator.username : 'Anonymous'}
                </p>
                {puzzle.description && (
                  <p className="mt-2 text-[13px] text-muted-foreground line-clamp-2">
                    {puzzle.description}
                  </p>
                )}
              </div>
              {puzzle.is_solved ? (
                <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 rounded-md px-2 py-0.5 text-[11px] font-medium">
                  <CheckCircle2 className="size-3.5" />
                  <span>Solved</span>
                  {puzzle.best_medal && puzzle.best_medal >= 1 && (
                    <span className="ml-1">
                      {puzzle.best_medal >= 3 ? '🥇' : puzzle.best_medal === 2 ? '🥈' : '🥉'}
                    </span>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-1 bg-secondary text-muted-foreground rounded-md px-2 py-0.5 text-[11px] font-medium">
                  <Medal className="size-3.5" />
                  <span>Unsolved</span>
                </div>
              )}
            </div>

            {/* Best Time (if solved) */}
            {puzzle.is_solved && puzzle.best_time != null && (
              <div className="mb-3 flex items-center gap-1 text-[13px] text-emerald-600">
                <Clock className="size-3.5" />
                <span>Best Time: {Math.floor(puzzle.best_time / 60)}:{String(puzzle.best_time % 60).padStart(2, '0')}</span>
              </div>
            )}

            {/* XP Progress Bar */}
            <div className="mb-3 rounded-lg bg-secondary/50 p-3">
              <PuzzleXPBar
                difficulty={puzzle.difficulty}
                avgDifficulty={puzzle.avg_difficulty ?? 0}
                currentXP={puzzle.total_xp ?? 0}
              />
            </div>

            {/* Difficulty, plays, and save button row */}
            <div className="mb-3 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded border px-2 py-1 text-xs ${getDifficultyColor(
                    puzzle.difficulty,
                  )}`}
                >
                  {puzzle.difficulty.charAt(0) +
                    puzzle.difficulty.slice(1).toLowerCase()}
                </span>
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Users className="size-3.5" />
                  <span className="text-[13px]">
                    {puzzle.solvedCount || 0} solved
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className={cn(
                  'text-[13px] flex items-center gap-2',
                  puzzle.is_saved && 'border-yellow-200/60 bg-yellow-50/50'
                )}
                onClick={() => saveMutation.mutate({ puzzleId: puzzle.id })}
                isLoading={saveMutation.isPending}
              >
                {puzzle.is_saved ? '⭐' : '🔖'} {puzzle.is_saved ? 'Saved' : 'Save'}
              </Button>
            </div>

            {/* Instructions and Comment buttons row */}
            <div className={`mb-3 flex flex-wrap items-center ${puzzle.creatorComment ? 'gap-6' : 'justify-center'}`}>
              <Button
                variant="outline"
                size="sm"
                className={`text-[13px] flex items-center ${puzzle.creatorComment ? 'flex-1' : ''}`}
                onClick={() => setDetailsPuzzleId(puzzle.id)}
              >
                📋 Instructions
              </Button>
              {puzzle.creatorComment && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[13px] flex items-center gap-2 flex-1 shadow-none ring-0 whitespace-nowrap"
                  onClick={() => setCommentPuzzleId(puzzle.id)}
                >
                  💬 Comment
                </Button>
              )}
            </div>

            {/* Rating and leaderboard */}
            <div className="flex flex-wrap items-start gap-3 border-t border-border pt-3">
              {/* Already Rated Badge */}
              {puzzle.user_rating && (
                <div className="flex items-center gap-1 rounded-md border border-amber-200/60 bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700 w-full">
                  <Star className="size-3.5 fill-amber-400 text-amber-400" />
                  <span>You already rated this puzzle</span>
                </div>
              )}

              {/* Weighted Difficulty — clickable to open rating dialog */}
              <button
                type="button"
                className={`flex flex-col gap-0.5 rounded px-1.5 py-1 text-left transition-colors ${
                  puzzle.can_rate
                    ? 'cursor-pointer hover:bg-secondary/80'
                    : 'cursor-default opacity-80'
                }`}
                title={
                  puzzle.can_rate
                    ? 'Click to rate this puzzle'
                    : `Solve or spend ${puzzle.rating_min_attempt_seconds ?? 10} sec to rate`
                }
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Difficulty
                </span>
                <div className="flex items-center gap-1">
                  {puzzle.rating_metrics && puzzle.rating_metrics.count > 0 ? (
                    <>
                      {renderStars(puzzle.rating_metrics.weighted_difficulty)}
                      <span className="ml-1 text-[13px] text-muted-foreground">
                        {puzzle.rating_metrics.weighted_difficulty.toFixed(1)}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      No Ratings
                    </span>
                  )}
                </div>
              </button>

              {/* Fun Rating — clickable to open rating dialog */}
              <button
                type="button"
                className={`flex flex-col gap-0.5 rounded px-1.5 py-1 text-left transition-colors ${
                  puzzle.can_rate
                    ? 'cursor-pointer hover:bg-secondary/80'
                    : 'cursor-default opacity-80'
                }`}
                title={
                  puzzle.can_rate
                    ? 'Click to rate this puzzle'
                    : `Solve or spend ${puzzle.rating_min_attempt_seconds ?? 10} sec to rate`
                }
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Fun
                </span>
                <div className="flex items-center gap-1">
                  {puzzle.rating_metrics?.avg_fun != null ? (
                    <>
                      <span className="text-xl leading-none" title={`Fun: ${puzzle.rating_metrics.avg_fun.toFixed(1)}/5`}>
                        {puzzle.rating_metrics.avg_fun < 2
                          ? '😞'
                          : puzzle.rating_metrics.avg_fun < 3.5
                            ? '😊'
                            : '😄'}
                      </span>
                      <span className="ml-1 text-[13px] text-muted-foreground">
                        {puzzle.rating_metrics.avg_fun.toFixed(1)}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      Needs Votes
                    </span>
                  )}
                </div>
              </button>

              {/* Clearness — clickable to open rating dialog */}
              <button
                type="button"
                className={`flex flex-col gap-0.5 rounded px-1.5 py-1 text-left transition-colors ${
                  puzzle.can_rate
                    ? 'cursor-pointer hover:bg-secondary/80'
                    : 'cursor-default opacity-80'
                }`}
                title={
                  puzzle.can_rate
                    ? 'Click to rate this puzzle'
                    : `Solve or spend ${puzzle.rating_min_attempt_seconds ?? 10} sec to rate`
                }
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Clearness
                </span>
                <div className="flex items-center gap-1">
                  {puzzle.rating_metrics?.avg_clearness != null ? (
                    <>
                      <span className="text-xl leading-none" title={`Clearness: ${puzzle.rating_metrics.avg_clearness.toFixed(1)}/5`}>
                        {puzzle.rating_metrics.avg_clearness < 2
                          ? '❌'
                          : puzzle.rating_metrics.avg_clearness < 3.5
                            ? '💡'
                            : '✨'}
                      </span>
                      <span className="ml-1 text-[13px] text-muted-foreground">
                        {puzzle.rating_metrics.avg_clearness < 2
                          ? 'Not clear'
                          : puzzle.rating_metrics.avg_clearness < 3.5
                            ? 'Clear'
                            : 'Very clear'}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      Needs Votes
                    </span>
                  )}
                </div>
              </button>

              <div className="w-full flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2 text-[13px] sm:w-40 whitespace-nowrap"
                  onClick={() => setLeaderboardPuzzleId(puzzle.id)}
                >
                  🏆 Leaderboard
                </Button>
              </div>
            </div>

            {/* Primary action */}
            <div className="mt-4 flex justify-center">
              <Link
                href={paths.app.puzzle.getHref(puzzle.id)}
                className="w-full max-w-xs rounded-lg bg-foreground px-4 py-3 text-center text-sm font-semibold text-background shadow-md transition-colors hover:bg-foreground/90"
              >
                Solve Puzzle
              </Link>
            </div>
            </div>
          );
          })}
          </div>
        </div>
      )}

      <PuzzleDetailsDialog
        puzzle={selectedPuzzle}
        open={Boolean(selectedPuzzle)}
        onOpenChange={(open) => {
          if (!open) setDetailsPuzzleId(null);
        }}
        showLink={true}
      />

      <CreatorCommentDialog
        puzzle={selectedCommentPuzzle}
        open={Boolean(selectedCommentPuzzle)}
        onOpenChange={(open) => {
          if (!open) setCommentPuzzleId(null);
        }}
        showLink={true}
      />

      {leaderboardPuzzleId && selectedLeaderboardPuzzle && (
        <Dialog open={true} onOpenChange={(open) => {
          if (!open) setLeaderboardPuzzleId(null);
        }}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Trophy className="size-5 text-amber-500" />
                Leaderboard
              </DialogTitle>
              <DialogDescription>
                Top solvers for this puzzle
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-[60vh] overflow-y-auto">
              <PuzzleLeaderboard puzzleId={selectedLeaderboardPuzzle.id} />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setLeaderboardPuzzleId(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {ratingPuzzleId && (
        <RatingDialog
          puzzleId={ratingPuzzleId}
          open={true}
          onOpenChange={(open) => {
            if (!open) setRatingPuzzleId(null);
          }}
        />
      )}

      {/* Pagination */}
      {!puzzlesQuery.isLoading && meta && meta.totalPages > 1 && (
        <div className="mt-8 flex justify-center gap-2">
          {Array.from({ length: meta.totalPages }, (_, i) => i + 1).map(
            (pageNum) => (
              <button
                type="button"
                key={pageNum}
                onClick={() => setFilters((prev) => ({ ...prev, page: pageNum }))}
                className={`rounded-lg border px-3 py-2 text-sm ${pageNum === meta.page
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-border bg-card text-foreground hover:bg-secondary'
                  }`}
              >
                {pageNum}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
};
