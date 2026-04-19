'use client';

import { Bookmark, Users } from 'lucide-react';

import { Link } from '@/components/ui/link';
import { PuzzleXPBar } from '@/components/ui/puzzle-xp-bar';
import { paths } from '@/config/paths';
import type { Puzzle } from '@/types/api';
import { cn } from '@/utils/cn';

import { formatTime } from '../utils/format-time';

import { PuzzleActionCluster } from './puzzle-action-cluster';
import { PuzzleRatingChips } from './puzzle-rating-chips';
import { PuzzleStatusIndicator } from './puzzle-status-indicator';

interface PuzzleCardProps {
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

export const PuzzleCard = ({
  puzzle,
  onRate,
  onInstructions,
  onComment,
  onLeaderboard,
  onSave,
  savingPuzzleId,
}: PuzzleCardProps) => {
  const href = paths.app.puzzle.getHref(puzzle.id);
  const isSaving = savingPuzzleId === puzzle.id;

  return (
    <article
      className={cn(
        'group relative flex min-h-[320px] flex-col rounded-xl border border-border bg-card p-4 shadow-subtle',
        'transition-colors hover:shadow-card',
      )}
    >
      {/* Left status stripe */}
      <PuzzleStatusIndicator
        isSolved={puzzle.is_solved}
        medal={puzzle.best_medal}
        variant="stripe"
      />

      {/* Top row: difficulty pill + solved count + save */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'shrink-0 rounded border px-2 py-0.5 text-xs',
              getDifficultyClass(puzzle.difficulty),
            )}
          >
            {puzzle.difficulty.charAt(0) +
              puzzle.difficulty.slice(1).toLowerCase()}
          </span>
          <div className="flex items-center gap-1 font-mono text-[12px] text-muted-foreground">
            <Users className="size-3" aria-hidden />
            <span>{puzzle.solvedCount ?? 0}</span>
          </div>
        </div>

        {/* Save button — relative z-10 so it sits above the stretched-link overlay */}
        <div className="relative z-10">
          <button
            type="button"
            className={cn(
              'puzzle-save-button',
              'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground',
              'transition-colors hover:bg-secondary hover:text-foreground',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
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
      </div>

      {/* Title — stretched-link anchor. The Link is NOT positioned, so the ::after
          positions against the card's relative root and covers the whole card.
          Sibling controls with `relative z-10` paint above the overlay. */}
      <Link
        href={href}
        className={cn(
          'line-clamp-2 text-[15px] font-medium leading-snug tracking-tight',
          'text-foreground hover:underline',
          "after:absolute after:inset-0 after:content-['']",
        )}
      >
        {puzzle.title}
      </Link>

      {/* Creator subtitle */}
      <p className="mt-1 text-[12.5px] text-muted-foreground">
        by {puzzle.creator ? puzzle.creator.username : 'Anonymous'}
      </p>

      {/* Description (2-line clamp; min-h preserves vertical rhythm even when absent) */}
      <p className="mt-1.5 line-clamp-2 min-h-[2.6em] text-[13px] text-muted-foreground">
        {puzzle.description || '\u00A0'}
      </p>

      {/* Stats row */}
      <div className="mt-2 flex items-center gap-2 font-mono text-[12px] text-muted-foreground">
        {puzzle.is_solved && puzzle.best_time != null && (
          <>
            <span>Best {formatTime(puzzle.best_time)}</span>
            <span aria-hidden>·</span>
          </>
        )}
        <span>{puzzle.solvedCount ?? 0} solved</span>
      </div>

      {/* XP bar */}
      <div className="mt-2">
        <PuzzleXPBar
          difficulty={puzzle.difficulty}
          avgDifficulty={puzzle.avg_difficulty ?? 0}
          currentXP={puzzle.total_xp ?? 0}
        />
      </div>

      {/* Rating chips — relative z-10 so chips intercept clicks above the stretched overlay */}
      <div className="relative z-10 mt-2.5">
        <PuzzleRatingChips
          metrics={puzzle.rating_metrics}
          userRating={puzzle.user_rating}
          canRate={puzzle.can_rate}
          minAttemptSeconds={puzzle.rating_min_attempt_seconds}
          onRate={() => onRate(puzzle.id)}
          size="card"
          weightedDifficulty={puzzle.rating_metrics?.weighted_difficulty}
        />
      </div>

      {/* Bottom bar: action cluster (left) + Solve button (right) — mt-auto sticks to bottom */}
      <div className="mt-auto flex items-center justify-between pt-3">
        <PuzzleActionCluster
          puzzle={puzzle}
          onInstructions={() => onInstructions(puzzle.id)}
          onComment={() => onComment(puzzle.id)}
          onLeaderboard={() => onLeaderboard(puzzle.id)}
          onRate={() => onRate(puzzle.id)}
          variant="card"
        />

        {/* Solve link — relative z-10 so it stays above the stretched-link overlay */}
        <div className="relative z-10">
          <Link
            href={href}
            className={cn(
              'puzzle-card-action',
              'inline-flex items-center justify-center gap-1 rounded-md px-3 py-1.5',
              'bg-primary text-[13px] font-medium text-primary-foreground',
              'transition-colors hover:bg-primary/90',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
            )}
          >
            Solve
          </Link>
        </div>
      </div>
    </article>
  );
};
