'use client';

import Link from 'next/link';

import { PuzzlesList } from '@/features/puzzles/components/puzzles-list';
import { useUser } from '@/lib/auth';

export const Puzzles = () => {
  const user = useUser();

  return (
    <div>
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
            Circuit Puzzles
          </h1>
          <p className="text-muted-foreground text-[13px]">
            Browse and solve challenging circuit design puzzles
          </p>
        </div>

        {/* Puzzles List */}
        <PuzzlesList />
      </div>
    </div>
  );
};
