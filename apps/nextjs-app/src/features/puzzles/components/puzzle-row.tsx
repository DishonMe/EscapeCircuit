'use client';

import { Bookmark, ChevronRight } from 'lucide-react';

import { Link } from '@/components/ui/link';
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';
import { cn } from '@/utils/cn';

import { formatFirstSolved } from '../utils/format-first-solved';
import { formatTime } from '../utils/format-time';

import { PuzzleActionCluster } from './puzzle-action-cluster';
import { PuzzleRatingChips } from './puzzle-rating-chips';
import { PuzzleStatusIndicator } from './puzzle-status-indicator';

interface PuzzleRowProps {
  puzzle: Puzzle;
  onRate: (puzzleId: string) => void;
  onInstructions: (puzzleId: string) => void;
  onComment: (puzzleId: string) => void;
  onLeaderboard: (puzzleId: string) => void;
  onSave: (puzzleId: string) => void;
  savingPuzzleId?: string | null;
}

function getDifficultyClass(difficulty: string): string {
  switch (difficulty.toLowerCase()) {
    case 'easy':
      return 'difficulty-badge difficulty-badge--easy';
    case 'medium':
      return 'difficulty-badge difficulty-badge--medium';
    case 'hard':
      return 'difficulty-badge difficulty-badge--hard';
    default:
      return 'border-border bg-secondary text-muted-foreground';
  }
}

const iconButtonClass =
  'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

export const PuzzleRow = ({
  puzzle,
  onRate,
  onInstructions,
  onComment,
  onLeaderboard,
  onSave,
  savingPuzzleId,
}: PuzzleRowProps) => {
  const href = paths.app.puzzle.getHref(puzzle.id);
  const isSaving = savingPuzzleId === puzzle.id;

  return (
    <div
      role="group"
      className={cn(
        'group relative flex h-14 items-center gap-4 border-b border-border px-4',
        'transition-colors hover:bg-secondary/30',
      )}
    >
      {/* Left stripe — visible only on group hover */}
      <PuzzleStatusIndicator
        isSolved={puzzle.is_solved}
        medal={puzzle.best_medal}
        variant="stripe"
        className="opacity-0 transition-opacity group-hover:opacity-100"
      />

      {/* Status dot — always visible */}
      <PuzzleStatusIndicator
        isSolved={puzzle.is_solved}
        medal={puzzle.best_medal}
        variant="dot"
        className="shrink-0"
      />

      {/* Title + creator stack — grows to fill space; title carries the stretched-link overlay.
          Neither the stack div nor the Link is positioned, so the Link's ::after positions
          against the row root's `relative` and covers the entire row. */}
      <div className="min-w-0 flex-1">
        <Link
          href={href}
          className={cn(
            'puzzle-card-action',
            'block truncate text-[14px] font-medium text-foreground hover:underline',
            "after:absolute after:inset-0 after:content-['']",
          )}
        >
          {puzzle.title}
        </Link>
        <p className="hidden truncate text-[12px] text-muted-foreground md:block">
          {puzzle.creator ? puzzle.creator.username : 'Anonymous'}
          {puzzle.is_solved && puzzle.first_solved_at
            ? ` · First Solved - ${formatFirstSolved(puzzle.first_solved_at)}`
            : ''}
        </p>
      </div>

      {/* Difficulty pill — fixed width, shown sm+ */}
      <span
        className={cn(
          'hidden w-20 shrink-0 rounded border px-2 py-0.5 text-center text-xs sm:inline-block',
          getDifficultyClass(puzzle.difficulty),
        )}
      >
        {puzzle.difficulty.charAt(0) + puzzle.difficulty.slice(1).toLowerCase()}
      </span>

      {/* Rating chips micro — shown sm+ */}
      <div className="relative z-10 hidden items-center sm:flex">
        <PuzzleRatingChips
          metrics={puzzle.rating_metrics}
          userRating={puzzle.user_rating}
          canRate={puzzle.can_rate}
          minAttemptSeconds={puzzle.rating_min_attempt_seconds}
          onRate={() => onRate(puzzle.id)}
          size="row"
          weightedDifficulty={puzzle.rating_metrics?.weighted_difficulty}
        />
      </div>

      {/* Best time — shown lg+ */}
      <span className="hidden w-16 shrink-0 font-mono text-[12px] text-muted-foreground lg:block">
        {puzzle.is_solved ? formatTime(puzzle.best_time) : '—'}
      </span>

      {/* Save button — inline, relative z-10 */}
      <div className="relative z-10 shrink-0">
        <button
          type="button"
          className={cn(
            iconButtonClass,
            'puzzle-save-button',
            isSaving && 'pointer-events-none opacity-50',
          )}
          aria-label={puzzle.is_saved ? 'Unsave puzzle' : 'Save puzzle'}
          onClick={() => onSave(puzzle.id)}
          disabled={isSaving}
        >
          <Bookmark
            className={cn(
              'size-4',
              puzzle.is_saved && 'fill-current text-primary',
            )}
            aria-hidden
          />
        </button>
      </div>

      {/* Kebab menu for Instructions / Comment / Leaderboard */}
      <PuzzleActionCluster
        puzzle={puzzle}
        onInstructions={() => onInstructions(puzzle.id)}
        onComment={() => onComment(puzzle.id)}
        onLeaderboard={() => onLeaderboard(puzzle.id)}
        variant="row"
      />

      {/* Trailing visual chevron — aria-hidden, indicates navigability */}
      <ChevronRight
        className="size-4 shrink-0 text-muted-foreground"
        aria-hidden
      />
    </div>
  );
};
