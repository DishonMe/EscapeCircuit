'use client';

import Link from 'next/link';

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

        {/* Create Puzzle Buttons */}
        <div className="mb-6 flex gap-3">
          <Link
            href="/app/create-puzzle"
            className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            ✏️ Create with Form
          </Link>
          <Link
            href="/app/admin/upload-puzzle"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            📤 Upload from Files
          </Link>
        </div>

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
