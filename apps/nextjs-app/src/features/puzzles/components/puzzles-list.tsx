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
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { useMemo, useState, ChangeEvent } from 'react';

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
import { Spinner } from '@/components/ui/spinner';
import { PuzzleXPBar } from '@/components/ui/puzzle-xp-bar';
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';
import { RatingDialog } from '@/features/ratings/components/rating-dialog';

import { usePuzzles, PuzzleFilters } from '../api/get-puzzles';
import { CreatorCommentDialog } from './creator-comment-dialog';
import { PuzzleDetailsDialog } from './puzzle-details-dialog';

export const PuzzlesList = () => {
  const searchParams = useSearchParams();
  const page = searchParams?.get('page') ? Number(searchParams.get('page')) : 1;

  const [detailsPuzzleId, setDetailsPuzzleId] = useState<string | null>(null);
  const [commentPuzzleId, setCommentPuzzleId] = useState<string | null>(null);
  const [ratingPuzzleId, setRatingPuzzleId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(true);
  const [filters, setFilters] = useState<PuzzleFilters>({ page: 1 });

  const puzzlesQuery = usePuzzles({
    filters: {
      page: filters.page || page,
      ...filters,
    },
  });

  const puzzles = puzzlesQuery.data?.data;
  const meta = puzzlesQuery.data?.meta;

  const selectedPuzzle: Puzzle | undefined = useMemo(() => {
    if (!detailsPuzzleId || !puzzles) return undefined;
    return puzzles.find((p) => p.id === detailsPuzzleId);
  }, [detailsPuzzleId, puzzles]);

  const selectedCommentPuzzle: Puzzle | undefined = useMemo(() => {
    if (!commentPuzzleId || !puzzles) return undefined;
    return puzzles.find((p) => p.id === commentPuzzleId);
  }, [commentPuzzleId, puzzles]);

  const isEmpty = !puzzles || puzzles.length === 0;

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'hard':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
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
              : 'text-gray-300'
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
            onClick={() => setFilters({ page: 1 })}
            className="text-gray-600"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
          {/* Top Level: name, min difficulty, min fun, min clearness */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Search Name */}
            <div>
              <label className="text-sm font-medium text-gray-700">Search Name</label>
              <input
                type="text"
                placeholder="Puzzle name..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.search || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, search: e.target.value || undefined, page: 1 })}
              />
            </div>

            {/* Min Difficulty */}
            <div>
              <label className="text-sm font-medium text-gray-700">Min Difficulty</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
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
              <label className="text-sm font-medium text-gray-700">Min Fun Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.minFun || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, minFun: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>

            {/* Min Clearness */}
            <div>
              <label className="text-sm font-medium text-gray-700">Min Clearness Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.minClearness || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, minClearness: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>
          </div>

          {/* Mid Level: order, max difficulty, max fun, max clearness */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Order By */}
            <div>
              <label className="text-sm font-medium text-gray-700">Order By</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
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
              <label className="text-sm font-medium text-gray-700">Max Difficulty</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
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
              <label className="text-sm font-medium text-gray-700">Max Fun Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.maxFun || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, maxFun: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>

            {/* Max Clearness */}
            <div>
              <label className="text-sm font-medium text-gray-700">Max Clearness Rating</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="0-5"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.maxClearness || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, maxClearness: e.target.value ? parseFloat(e.target.value) : undefined, page: 1 })}
              />
            </div>
          </div>

          {/* Last Level: direction, experienced/inexperienced/all */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Direction */}
            <div>
              <label className="text-sm font-medium text-gray-700">Direction</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderDirection || 'ASC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderDirection: e.target.value as any, page: 1 })}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
              </select>
            </div>

            {/* Experience Level */}
            <div>
              <label className="text-sm font-medium text-gray-700">Experience Level</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.experienceLevel || 'all'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, experienceLevel: e.target.value as any, page: 1 })}
              >
                <option value="all">All</option>
                <option value="experienced">Experienced</option>
                <option value="inexperienced">Inexperienced</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {puzzlesQuery.isLoading && (
        <div className="flex h-48 w-full items-center justify-center">
          <Spinner size="lg" />
        </div>
      )}

      {/* Empty state */}
      {!puzzlesQuery.isLoading && isEmpty && (
        <div className="rounded border border-gray-200 bg-white p-8 text-center text-gray-600">
          No puzzles available.
        </div>
      )}

      {/* Puzzle Grid */}
      {!puzzlesQuery.isLoading && !isEmpty && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {puzzles!.map((puzzle) => (
          <div
            key={puzzle.id}
            className={`relative cursor-pointer rounded-lg border-2 bg-white p-5 transition-all hover:shadow-lg ${
              puzzle.is_solved
                ? 'border-green-400 hover:border-green-500'
                : 'border-gray-300 hover:border-blue-400'
            }`}
          >
            {/* Solved checkmark overlay */}
            {puzzle.is_solved && (
              <div className="absolute -right-2 -top-2 z-10 flex size-8 items-center justify-center rounded-full bg-green-500 text-white shadow-md">
                <CheckCircle2 className="size-5" />
              </div>
            )}

          {/* Title & Creator with status badge */}
            <div className="mb-3 flex flex-wrap items-start gap-2">
              <div className="flex-1">
                <h3 className="mb-1 font-medium text-gray-900">{puzzle.title}</h3>
                <p className="text-sm text-gray-500">
                  by{' '}
                  {puzzle.creator ? puzzle.creator.username : 'Anonymous'}
                </p>
              </div>
              {puzzle.is_solved ? (
                <div className="flex items-center gap-1 rounded bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">
                  <CheckCircle2 className="size-3.5" />
                  <span>Solved</span>
                  {puzzle.best_medal && puzzle.best_medal >= 1 && (
                    <span className="ml-1">
                      {puzzle.best_medal >= 3 ? '🥇' : puzzle.best_medal === 2 ? '🥈' : '🥉'}
                    </span>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-gray-700">
                  <Medal className="size-3.5" />
                  <span>Unsolved</span>
                </div>
              )}
            </div>

            {/* Best Time (if solved) */}
            {puzzle.is_solved && puzzle.best_time != null && (
              <div className="mb-3 flex items-center gap-1 text-sm text-green-700">
                <Clock className="size-3.5" />
                <span>Best Time: {Math.floor(puzzle.best_time / 60)}:{String(puzzle.best_time % 60).padStart(2, '0')}</span>
              </div>
            )}

            {/* XP Progress Bar */}
            <div className="mb-3 rounded-md bg-gray-50 p-3">
              <PuzzleXPBar
                avgDifficulty={puzzle.avg_difficulty ?? 0}
                currentXP={puzzle.total_xp ?? 0}
                isSolved={puzzle.is_solved ?? false}
              />
            </div>

            {/* Difficulty, plays, and details */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span
                className={`rounded border px-2 py-1 text-xs ${getDifficultyColor(
                  puzzle.difficulty,
                )}`}
              >
                {puzzle.difficulty.charAt(0) +
                  puzzle.difficulty.slice(1).toLowerCase()}
              </span>
              <div className="flex items-center gap-1 text-gray-600">
                <Users className="size-3.5" />
                <span className="text-xs">
                  {puzzle.solvedCount || 0} solved
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="ml-auto w-full shadow-md ring-1 ring-blue-100 sm:w-40"
                onClick={() => setDetailsPuzzleId(puzzle.id)}
              >
                <Info className="mr-2 size-4" /> Puzzle details
              </Button>
            </div>

            {/* Rating and creator comment */}
            <div className="flex flex-wrap items-start gap-3 border-t border-gray-200 pt-3">
              {/* Weighted Difficulty — clickable to open rating dialog */}
              <button
                type="button"
                className={`flex flex-col gap-0.5 rounded px-1.5 py-1 text-left transition-colors ${
                  puzzle.can_rate
                    ? 'cursor-pointer hover:bg-yellow-50'
                    : 'cursor-default opacity-80'
                }`}
                title={puzzle.can_rate ? 'Click to rate this puzzle' : 'Solve or spend 5 min to rate'}
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                  Difficulty
                </span>
                <div className="flex items-center gap-1">
                  {puzzle.rating_metrics && puzzle.rating_metrics.count > 0 ? (
                    <>
                      {renderStars(puzzle.rating_metrics.weighted_difficulty)}
                      <span className="ml-1 text-xs text-gray-600">
                        {puzzle.rating_metrics.weighted_difficulty.toFixed(1)}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">
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
                    ? 'cursor-pointer hover:bg-yellow-50'
                    : 'cursor-default opacity-80'
                }`}
                title={puzzle.can_rate ? 'Click to rate this puzzle' : 'Solve or spend 5 min to rate'}
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
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
                      <span className="ml-1 text-xs text-gray-600">
                        {puzzle.rating_metrics.avg_fun.toFixed(1)}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
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
                    ? 'cursor-pointer hover:bg-yellow-50'
                    : 'cursor-default opacity-80'
                }`}
                title={puzzle.can_rate ? 'Click to rate this puzzle' : 'Solve or spend 5 min to rate'}
                onClick={() => {
                  if (puzzle.can_rate) setRatingPuzzleId(puzzle.id);
                }}
              >
                <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
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
                      <span className="ml-1 text-xs text-gray-600">
                        {puzzle.rating_metrics.avg_clearness < 2
                          ? 'Not clear'
                          : puzzle.rating_metrics.avg_clearness < 3.5
                            ? 'Clear'
                            : 'Very clear'}
                      </span>
                    </>
                  ) : (
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                      Needs Votes
                    </span>
                  )}
                </div>
              </button>

              <div className="ml-auto">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center w-full sm:w-40"
                  disabled={!puzzle.creatorComment}
                  onClick={() => {
                    if (puzzle.creatorComment) setCommentPuzzleId(puzzle.id);
                  }}
                >
                  <MessageSquare className="mr-2 size-4" />
                  {puzzle.creatorComment ? 'Creator comment' : 'No creator comment'}
                </Button>
              </div>
            </div>

            {/* Primary action */}
            <div className="mt-4 flex justify-center">
              <Link
                href={paths.app.puzzle.getHref(puzzle.id)}
                className="w-full max-w-xs rounded bg-blue-600 px-4 py-3 text-center text-sm font-semibold text-white shadow-md transition-colors hover:bg-blue-700"
              >
                Solve Puzzle
              </Link>
            </div>
          </div>
        ))}
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
              <Link
                key={pageNum}
                href={`${paths.app.puzzles.getHref()}?page=${pageNum}`}
                className={`rounded border px-3 py-2 text-sm ${pageNum === meta.page
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
              >
                {pageNum}
              </Link>
            ),
          )}
        </div>
      )}
    </div>
  );
};
