'use client';

import { X } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface PuzzlesEmptyProps {
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

export const PuzzlesEmpty = ({
  hasActiveFilters,
  onClearFilters,
}: PuzzlesEmptyProps) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {/* AND gate glyph */}
      <svg
        width="64"
        height="64"
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-muted-foreground/40"
        aria-hidden
      >
        {/* Input lines */}
        <line
          x1="4"
          y1="20"
          x2="18"
          y2="20"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        <line
          x1="4"
          y1="44"
          x2="18"
          y2="44"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
        {/* AND gate body: flat left side + rounded right */}
        <path
          d="M18 12 L18 52 L34 52 Q52 52 52 32 Q52 12 34 12 Z"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          strokeLinejoin="round"
        />
        {/* Output line */}
        <line
          x1="52"
          y1="32"
          x2="60"
          y2="32"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>

      <h2 className="mt-4 text-[15px] font-medium text-foreground">
        {hasActiveFilters
          ? 'No puzzles match your filters.'
          : 'No puzzles available yet.'}
      </h2>

      <p className="mt-1 text-[13px] text-muted-foreground">
        {hasActiveFilters
          ? 'Try adjusting or clearing your filters to see more results.'
          : 'Check back soon — new puzzles are added regularly.'}
      </p>

      {hasActiveFilters && (
        <Button
          variant="outline"
          size="sm"
          onClick={onClearFilters}
          className="mt-4 gap-1.5"
        >
          <X className="size-4" aria-hidden />
          Clear filters
        </Button>
      )}
    </div>
  );
};
