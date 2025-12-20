'use client';

import { PuzzlesList } from '@/features/puzzles/components/puzzles-list';

export const Puzzles = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Circuit Puzzles
          </h1>
          <p className="text-gray-600">
            Browse and solve challenging circuit design puzzles
          </p>
        </div>

        {/* Create Puzzle Button */}
        <div className="mb-6">
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium">
            Create New Puzzle
          </button>
        </div>

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
