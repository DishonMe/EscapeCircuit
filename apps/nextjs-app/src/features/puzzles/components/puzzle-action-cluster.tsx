'use client';

import { BookOpen, MessageSquare, MoreHorizontal, Trophy } from 'lucide-react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown/dropdown';
import type { Puzzle } from '@/types/api';
import { cn } from '@/utils/cn';

interface PuzzleActionClusterProps {
  puzzle: Puzzle;
  onInstructions: () => void;
  onComment: () => void;
  onLeaderboard: () => void;
  /** Not used here — Save lives in the parent (puzzle-card / puzzle-row). */
  onSave?: () => void;
  variant: 'card' | 'row';
}

const iconButtonClass =
  'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

export const PuzzleActionCluster = ({
  puzzle,
  onInstructions,
  onComment,
  onLeaderboard,
  variant,
}: PuzzleActionClusterProps) => {
  if (variant === 'card') {
    return (
      <div className="relative z-10 flex items-center gap-1">
        <button
          type="button"
          // eslint-disable-next-line tailwindcss/no-custom-classname
          className={cn(iconButtonClass, 'puzzle-instructions-button')}
          aria-label="Instructions"
          onClick={onInstructions}
        >
          <BookOpen className="size-4" aria-hidden />
        </button>

        {puzzle.creatorComment && (
          <button
            type="button"
            className={cn(iconButtonClass)}
            aria-label="Creator comment"
            onClick={onComment}
          >
            <MessageSquare className="size-4" aria-hidden />
          </button>
        )}

        <button
          type="button"
          className={cn(iconButtonClass)}
          aria-label="Leaderboard"
          onClick={onLeaderboard}
        >
          <Trophy className="size-4" aria-hidden />
        </button>
      </div>
    );
  }

  // row variant: kebab menu only (Save is rendered inline by puzzle-row.tsx)
  return (
    <div className="relative z-10">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className={cn(iconButtonClass)}
            aria-label="More actions"
          >
            <MoreHorizontal className="size-4" aria-hidden />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            // eslint-disable-next-line tailwindcss/no-custom-classname
            className="puzzle-instructions-button flex cursor-pointer items-center gap-2"
            onSelect={onInstructions}
          >
            <BookOpen className="size-4" aria-hidden />
            Instructions
          </DropdownMenuItem>

          {puzzle.creatorComment && (
            <DropdownMenuItem
              className="flex cursor-pointer items-center gap-2"
              onSelect={onComment}
            >
              <MessageSquare className="size-4" aria-hidden />
              Creator Comment
            </DropdownMenuItem>
          )}

          <DropdownMenuItem
            className="flex cursor-pointer items-center gap-2"
            onSelect={onLeaderboard}
          >
            <Trophy className="size-4" aria-hidden />
            Leaderboard
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};
