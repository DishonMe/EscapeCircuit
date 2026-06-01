'use client';

import {
  BookOpen,
  MessageSquare,
  MoreHorizontal,
  Star,
  Trophy,
} from 'lucide-react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown/dropdown';
import type { Puzzle } from '@/types/api';
import { cn } from '@/utils/cn';

import { useInstructionsGlow } from '../hooks/use-instructions-glow';

interface PuzzleActionClusterProps {
  puzzle: Puzzle;
  onInstructions: () => void;
  onComment: () => void;
  onLeaderboard: () => void;
  onRate: () => void;
  /** Not used here — Save lives in the parent (puzzle-card / puzzle-row). */
  onSave?: () => void;
  variant: 'card' | 'row';
}

const iconButtonClass =
  'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

const buildRateTooltip = (
  canRate: boolean,
  hasRated: boolean,
  minAttemptSeconds?: number,
) => {
  if (!canRate) {
    return minAttemptSeconds != null
      ? `Solve or spend ${minAttemptSeconds} sec to rate`
      : 'Solve or spend the configured minimum time to rate';
  }
  return hasRated ? 'Update your rating' : 'Rate this puzzle';
};

export const PuzzleActionCluster = ({
  puzzle,
  onInstructions,
  onComment,
  onLeaderboard,
  onRate,
  variant,
}: PuzzleActionClusterProps) => {
  const canRate = !!puzzle.can_rate;
  const hasRated = !!puzzle.user_rating;
  const rateTooltip = buildRateTooltip(
    canRate,
    hasRated,
    puzzle.rating_min_attempt_seconds,
  );
  const { shouldGlow, markClicked } = useInstructionsGlow();

  const handleInstructionsClick = () => {
    markClicked();
    onInstructions();
  };

  if (variant === 'card') {
    return (
      <div className="relative z-10 flex items-center gap-1">
        <button
          type="button"
          className={cn(
            iconButtonClass,
            // eslint-disable-next-line tailwindcss/no-custom-classname
            'puzzle-instructions-button',
            // eslint-disable-next-line tailwindcss/no-custom-classname
            shouldGlow && 'puzzle-instructions-glow',
          )}
          aria-label="Instructions"
          onClick={handleInstructionsClick}
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
          className={cn(iconButtonClass, 'puzzle-leaderboard-button')}
          aria-label="Leaderboard"
          onClick={onLeaderboard}
        >
          <Trophy className="size-4" aria-hidden />
        </button>

        <button
          type="button"
          className={cn(
            iconButtonClass,
            'transition-transform',
            canRate &&
              'hover:scale-110 hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-950/40 dark:hover:text-amber-400',
            hasRated && 'text-amber-500',
            !canRate &&
              'opacity-50 hover:bg-transparent hover:text-muted-foreground cursor-not-allowed',
          )}
          aria-label={hasRated ? 'Update rating' : 'Rate puzzle'}
          aria-disabled={!canRate || undefined}
          title={rateTooltip}
          onClick={() => {
            if (canRate) onRate();
          }}
        >
          <Star
            className={cn(
              'size-4',
              hasRated && 'fill-amber-400 text-amber-500',
            )}
            aria-hidden
          />
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
            onSelect={handleInstructionsClick}
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
            className="puzzle-leaderboard-button flex cursor-pointer items-center gap-2"
            onSelect={onLeaderboard}
          >
            <Trophy className="size-4" aria-hidden />
            Leaderboard
          </DropdownMenuItem>

          <DropdownMenuItem
            className={cn(
              'flex cursor-pointer items-center gap-2',
              !canRate && 'cursor-not-allowed opacity-50',
            )}
            disabled={!canRate}
            title={rateTooltip}
            onSelect={(e) => {
              if (!canRate) {
                e.preventDefault();
                return;
              }
              onRate();
            }}
          >
            <Star
              className={cn(
                'size-4',
                hasRated ? 'fill-amber-400 text-amber-500' : '',
              )}
              aria-hidden
            />
            {hasRated ? 'Update Rating' : 'Rate Puzzle'}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};
