'use client';

import { Clock, Star, Circle, Users } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

import { Link } from '@/components/ui/link';
import { Spinner } from '@/components/ui/spinner';
import { paths } from '@/config/paths';

import { usePuzzles } from '../api/get-puzzles';

export const PuzzlesList = () => {
  const searchParams = useSearchParams();
  const page = searchParams?.get('page') ? Number(searchParams.get('page')) : 1;

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
            {/* Title & Creator */}
            <div className="mb-3">
              <h3 className="mb-1 font-medium text-gray-900">{puzzle.title}</h3>
              <p className="text-sm text-gray-500">
                by{' '}
                {puzzle.creator
                  ? `${puzzle.creator.username}`
                  : 'Anonymous'}
              </p>
            </div>

            {/* Difficulty & Time Limit */}
            <div className="mb-3 flex items-center gap-2">
              <span
                className={`rounded border px-2 py-1 text-xs ${getDifficultyColor(
                  puzzle.difficulty,
                )}`}
              >
                {puzzle.difficulty.charAt(0) +
                  puzzle.difficulty.slice(1).toLowerCase()}
              </span>
              <div className="flex items-center gap-1 text-gray-600">
                <Clock className="size-3.5" />
                <span className="text-xs">
                  {Math.floor(puzzle.timeLimit / 60)}:
                  {(puzzle.timeLimit % 60).toString().padStart(2, '0')}
                </span>
              </div>
              <div className="flex items-center gap-1 text-gray-600">
                <Users className="size-3.5" />
                <span className="text-xs">
                  {puzzle.solvedCount || 0} solved
                </span>
              </div>
            </div>

            {/* Rating & Solved Status */}
            <div className="flex items-center justify-between border-t border-gray-200 pt-3">
              {/* Rating */}
              <div className="flex items-center gap-1">
                {renderStars(puzzle.rating || 0)}
                <span className="ml-1 text-xs text-gray-600">
                  {(puzzle.rating || 0).toFixed(1)}
                </span>
              </div>

              {/* Solved Status */}
              <div className="flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-gray-500">
                <Circle className="size-3.5" />
                <span>Unsolved</span>
              </div>
            </div>

            {/* Action Button */}
            <div className="mt-4">
              <Link
                href={paths.app.puzzle.getHref(puzzle.id)}
                className="w-full rounded bg-blue-600 px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-blue-700"
              >
                Solve Puzzle
              </Link>
            </div>
          </div>
        ))}
      </div>

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
