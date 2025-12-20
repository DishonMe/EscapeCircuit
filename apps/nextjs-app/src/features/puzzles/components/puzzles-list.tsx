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
          className={`w-3.5 h-3.5 ${
            i <= Math.floor(rating)
              ? 'text-yellow-500 fill-yellow-500'
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {puzzles.map((puzzle) => (
          <div
            key={puzzle.id}
            className="bg-white border border-gray-300 rounded-lg p-5 hover:border-blue-400 hover:shadow-lg transition-all cursor-pointer relative"
          >
            {/* Title & Creator */}
            <div className="mb-3">
              <h3 className="text-gray-900 font-medium mb-1">{puzzle.title}</h3>
              <p className="text-sm text-gray-500">
                by{' '}
                {puzzle.creator
                  ? `${puzzle.creator.firstName} ${puzzle.creator.lastName}`
                  : 'Anonymous'}
              </p>
            </div>

            {/* Difficulty & Time Limit */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className={`px-2 py-1 border rounded text-xs ${getDifficultyColor(
                  puzzle.difficulty,
                )}`}
              >
                {puzzle.difficulty.charAt(0) +
                  puzzle.difficulty.slice(1).toLowerCase()}
              </span>
              <div className="flex items-center gap-1 text-gray-600">
                <Clock className="w-3.5 h-3.5" />
                <span className="text-xs">
                  {Math.floor(puzzle.timeLimit / 60)}:
                  {(puzzle.timeLimit % 60).toString().padStart(2, '0')}
                </span>
              </div>
              <div className="flex items-center gap-1 text-gray-600">
                <Users className="w-3.5 h-3.5" />
                <span className="text-xs">
                  {puzzle.solvedCount || 0} solved
                </span>
              </div>
            </div>

            {/* Rating & Solved Status */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              {/* Rating */}
              <div className="flex items-center gap-1">
                {renderStars(puzzle.rating || 0)}
                <span className="text-xs text-gray-600 ml-1">
                  {(puzzle.rating || 0).toFixed(1)}
                </span>
              </div>

              {/* Solved Status */}
              <div className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-gray-50 text-gray-500">
                <Circle className="w-3.5 h-3.5" />
                <span>Unsolved</span>
              </div>
            </div>

            {/* Action Button */}
            <div className="mt-4">
              <Link
                href={paths.app.puzzle.getHref(puzzle.id)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white text-center py-2 px-4 rounded text-sm font-medium transition-colors"
              >
                Solve Puzzle
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {meta && meta.totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: meta.totalPages }, (_, i) => i + 1).map(
            (pageNum) => (
              <Link
                key={pageNum}
                href={`${paths.app.puzzles.getHref()}?page=${pageNum}`}
                className={`px-3 py-2 border rounded text-sm ${
                  pageNum === meta.page
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
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
