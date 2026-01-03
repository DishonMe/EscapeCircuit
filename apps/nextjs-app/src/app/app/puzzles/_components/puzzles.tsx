'use client';

import { PuzzlesList } from '@/features/puzzles/components/puzzles-list';

export const Puzzles = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-900">
            Circuit Puzzles
          </h1>
          <p className="text-gray-600">
            Browse and solve challenging circuit design puzzles
          </p>
        </div>

        {/* Create Puzzle Button */}
        <div className="mb-6">
          <button className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Create New Puzzle
          </button>
        </div>

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
