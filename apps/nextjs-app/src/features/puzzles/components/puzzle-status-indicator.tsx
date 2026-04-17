'use client';

import { cn } from '@/utils/cn';

/** Medal tier color map — fixed universal colors, not palette-dependent. */
export const STATUS_COLORS: Record<string, string> = {
  unsolved: 'hsl(var(--border) / 0.6)',
  solved: 'rgb(16 185 129 / 0.6)', // emerald-500/60
  bronze: 'rgb(217 119 6)', // amber-600
  silver: 'rgb(148 163 184)', // slate-400
  gold: 'rgb(234 179 8)', // yellow-500
};

function getStatusKey(
  isSolved?: boolean,
  medal?: number | null,
): keyof typeof STATUS_COLORS {
  if (!isSolved) return 'unsolved';
  if (!medal || medal === 0) return 'solved';
  if (medal === 1) return 'bronze';
  if (medal === 2) return 'silver';
  return 'gold';
}

interface PuzzleStatusIndicatorProps {
  isSolved?: boolean;
  medal?: number | null;
  variant: 'stripe' | 'dot';
  className?: string;
}

export const PuzzleStatusIndicator = ({
  isSolved,
  medal,
  variant,
  className,
}: PuzzleStatusIndicatorProps) => {
  const statusKey = getStatusKey(isSolved, medal);
  const color = STATUS_COLORS[statusKey];

  if (variant === 'stripe') {
    return (
      <div
        aria-hidden
        className={cn(
          'absolute left-0 top-0 h-full w-0.5 rounded-l-xl',
          className,
        )}
        style={{ backgroundColor: color }}
      />
    );
  }

  // dot variant
  if (!isSolved) {
    return (
      <span
        aria-hidden
        className={cn(
          'inline-block size-4 shrink-0 rounded-full border border-border bg-transparent',
          className,
        )}
      />
    );
  }

  return (
    <span
      aria-hidden
      className={cn('inline-block size-4 shrink-0 rounded-full', className)}
      style={{ backgroundColor: color }}
    />
  );
};
