'use client';

import {
  Clock,
  Star,
  Circle,
  Users,
  Info,
  MessageSquare,
  Medal,
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

export const PuzzlesList = () => {
  const searchParams = useSearchParams();
  const page = searchParams?.get('page') ? Number(searchParams.get('page')) : 1;

  const [detailsPuzzleId, setDetailsPuzzleId] = useState<string | null>(null);
  const [commentPuzzleId, setCommentPuzzleId] = useState<string | null>(null);

  const puzzlesQuery = usePuzzles({
    page: page,
  });

  if (puzzlesQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

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

  if (!puzzles) return null;

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
      {/* Puzzle Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {puzzles.map((puzzle) => (
          <div
            key={puzzle.id}
            className="relative cursor-pointer rounded-lg border border-gray-300 bg-white p-5 transition-all hover:border-blue-400 hover:shadow-lg"
          >
          {/* Title & Creator with status badge */}
            <div className="mb-3 flex flex-wrap items-start gap-2">
              <div className="flex-1">
                <h3 className="mb-1 font-medium text-gray-900">{puzzle.title}</h3>
                <p className="text-sm text-gray-500">
                  by{' '}
                  {puzzle.creator
                    ? `${puzzle.creator.firstName} ${puzzle.creator.lastName}`
                    : 'Anonymous'}
                </p>
              </div>
              <div className="flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-gray-700">
                <Medal className="size-3.5" />
                <span>Unsolved</span>
              </div>
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

      <Dialog
        open={Boolean(selectedPuzzle)}
        onOpenChange={(open) => {
          if (!open) setDetailsPuzzleId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedPuzzle?.title ?? 'Puzzle details'}</DialogTitle>
            <DialogDescription>
              Key information before you start solving.
            </DialogDescription>
          </DialogHeader>

          {selectedPuzzle ? (
            <div className="space-y-3 text-sm text-gray-700">
              <div>
                <div className="font-medium text-gray-900">Description</div>
                <div className="mt-1 whitespace-pre-wrap">
                  {selectedPuzzle.description}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 rounded border border-gray-200 bg-gray-50 p-3 text-sm sm:grid-cols-2">
                <div>
                  <span className="font-medium text-gray-900">Time:</span>{' '}
                  {Math.floor(selectedPuzzle.timeLimit / 60)}m{' '}
                  {(selectedPuzzle.timeLimit % 60).toString().padStart(2, '0')}
                  s
                </div>
                <div>
                  <span className="font-medium text-gray-900">Budget:</span>{' '}
                  {selectedPuzzle.budgetLimit}
                </div>
                <div>
                  <span className="font-medium text-gray-900">Tight budget:</span>{' '}
                  {selectedPuzzle.tightBudgetLimit ?? '—'}
                </div>
              </div>

              <div>
                <div className="font-medium text-gray-900">Additional constraints (optional)</div>
                <div className="mt-1 space-y-1">
                  {Array.isArray(selectedPuzzle.additionalConstraints) ? (
                    selectedPuzzle.additionalConstraints.length > 0 ? (
                      <ul className="list-disc space-y-1 pl-5">
                        {selectedPuzzle.additionalConstraints.map((c) => (
                          <li key={c}>{c}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="text-gray-500">None provided.</div>
                    )
                  ) : selectedPuzzle.additionalConstraints ? (
                    <div>{selectedPuzzle.additionalConstraints}</div>
                  ) : (
                    <div className="text-gray-500">None provided.</div>
                  )}
                </div>
              </div>
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsPuzzleId(null)}>
              Close
            </Button>
            {selectedPuzzle ? (
              <Link
                href={paths.app.puzzle.getHref(selectedPuzzle.id)}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Go to puzzle
              </Link>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(selectedCommentPuzzle)}
        onOpenChange={(open) => {
          if (!open) setCommentPuzzleId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedCommentPuzzle?.title ?? 'Creator comment'}
            </DialogTitle>
            <DialogDescription>Notes from the puzzle creator.</DialogDescription>
          </DialogHeader>

          <div className="text-sm text-gray-700">
            <div className="font-medium text-gray-900">Creator comment</div>
            <div className="mt-1 whitespace-pre-wrap">
              {selectedCommentPuzzle?.creatorComment}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCommentPuzzleId(null)}>
              Close
            </Button>
            {selectedCommentPuzzle ? (
              <Link
                href={paths.app.puzzle.getHref(selectedCommentPuzzle.id)}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Go to puzzle
              </Link>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pagination */}
      {meta && meta.totalPages > 1 && (
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
