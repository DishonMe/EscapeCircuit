'use client';

import Link from 'next/link';

import { PuzzlesList } from '@/features/puzzles/components/puzzles-list';
import { useUser } from '@/lib/auth';

export const Puzzles = () => {
  const user = useUser();

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

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
