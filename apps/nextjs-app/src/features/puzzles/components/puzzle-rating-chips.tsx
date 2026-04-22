'use client';

import { Lightbulb, Smile, Star } from 'lucide-react';

import type { RatingEntry, RatingMetrics } from '@/types/api';
import { cn } from '@/utils/cn';

interface PuzzleRatingChipsProps {
  metrics?: RatingMetrics;
  userRating?: RatingEntry | null;
  canRate?: boolean;
  minAttemptSeconds?: number;
  onRate: () => void;
  size: 'card' | 'row';
  weightedDifficulty?: number;
}

function renderStars(rating: number) {
  const stars = [];
  for (let i = 1; i <= 5; i++) {
    stars.push(
      <Star
        key={i}
        className={cn(
          'size-3',
          i <= Math.floor(rating)
            ? 'fill-yellow-500 text-yellow-500'
            : 'text-muted-foreground/40',
        )}
      />,
    );
  }
  return stars;
}

function buildTooltip(canRate: boolean, minAttemptSeconds?: number): string {
  if (canRate) return 'Click to rate this puzzle';
  if (minAttemptSeconds != null) {
    return `Solve or spend ${minAttemptSeconds} sec to rate`;
  }
  return 'Solve or spend the configured minimum time to rate';
}

export const PuzzleRatingChips = ({
  metrics,
  userRating,
  canRate = false,
  minAttemptSeconds,
  onRate,
  size,
  weightedDifficulty,
}: PuzzleRatingChipsProps) => {
  const tooltip = buildTooltip(canRate, minAttemptSeconds);
  const hasRated = !!userRating;

  const chipBase = cn(
    'relative z-10 inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
    size === 'card' ? 'text-[12px] font-mono' : 'text-[11px]',
    canRate ? 'cursor-pointer' : 'cursor-default',
  );

  const handleClick = () => {
    if (canRate) onRate();
  };

  const difficultyVal =
    weightedDifficulty ?? metrics?.weighted_difficulty ?? null;

  return (
    // eslint-disable-next-line tailwindcss/no-custom-classname
    <div
      className="puzzle-rating-section flex flex-wrap items-center gap-1.5"
      role="group"
      aria-label="Rating"
    >
      {/* Difficulty chip */}
      <button
        type="button"
        className={cn(
          chipBase,
          'bg-amber-500/10',
          canRate && 'hover:bg-secondary/60',
        )}
        onClick={handleClick}
        aria-disabled={!canRate || undefined}
        title={tooltip}
      >
        {difficultyVal != null && difficultyVal > 0 ? (
          <>
            <span className="flex items-center gap-0.5">
              {renderStars(difficultyVal)}
            </span>
            <span className="ml-0.5">{difficultyVal.toFixed(1)}</span>
          </>
        ) : (
          <>
            <Star className="size-3 text-muted-foreground/40" />
            <span className="text-muted-foreground">—</span>
          </>
        )}
        {hasRated && (
          <span
            // eslint-disable-next-line tailwindcss/classnames-order
            className="size-1.5 shrink-0 rounded-full bg-foreground/60"
            aria-hidden
          />
        )}
      </button>

      {/* Fun chip */}
      <button
        type="button"
        className={cn(
          chipBase,
          'bg-violet-500/10',
          canRate && 'hover:bg-secondary/60',
        )}
        onClick={handleClick}
        aria-disabled={!canRate || undefined}
        title={tooltip}
      >
        <Smile className="size-3 shrink-0" />
        {metrics?.avg_fun != null ? (
          <span>{metrics.avg_fun.toFixed(1)}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
        {hasRated && (
          <span
            // eslint-disable-next-line tailwindcss/classnames-order
            className="size-1.5 shrink-0 rounded-full bg-foreground/60"
            aria-hidden
          />
        )}
      </button>

      {/* Clearness chip */}
      <button
        type="button"
        className={cn(
          chipBase,
          'bg-cyan-500/10',
          canRate && 'hover:bg-secondary/60',
        )}
        onClick={handleClick}
        aria-disabled={!canRate || undefined}
        title={tooltip}
      >
        <Lightbulb className="size-3 shrink-0" />
        {metrics?.avg_clearness != null ? (
          <span>{metrics.avg_clearness.toFixed(1)}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
        {hasRated && (
          <span
            // eslint-disable-next-line tailwindcss/classnames-order
            className="size-1.5 shrink-0 rounded-full bg-foreground/60"
            aria-hidden
          />
        )}
      </button>
    </div>
  );
};
