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
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { useMemo, useState } from 'react';

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
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';

import { usePuzzles } from '../api/get-puzzles';
import { CreatorCommentDialog } from './creator-comment-dialog';
import { PuzzleDetailsDialog } from './puzzle-details-dialog';

export const PuzzlesList = () => {
  const searchParams = useSearchParams();
  const page = searchParams?.get('page') ? Number(searchParams.get('page')) : 1;

  const [detailsPuzzleId, setDetailsPuzzleId] = useState<string | null>(null);
  const [commentPuzzleId, setCommentPuzzleId] = useState<string | null>(null);

  const puzzlesQuery = usePuzzles({
    page: page,
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
                {puzzle.total_xp ? (
                  <span className="ml-2 rounded bg-yellow-50 px-1.5 py-0.5 text-xs font-medium text-yellow-700">
                    +{puzzle.total_xp} XP
                  </span>
                ) : null}
              </div>
            )}

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
              <div className="flex items-center gap-1">
                {renderStars(puzzle.rating || 0)}
                <span className="ml-1 text-xs text-gray-600">
                  {(puzzle.rating || 0).toFixed(1)}
                </span>
              </div>
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
