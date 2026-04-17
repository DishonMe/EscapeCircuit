import type { ReactNode } from 'react';
import { Sparkles, Zap } from 'lucide-react';

type PuzzlesPageHeaderProps = {
  tutorialSlot?: ReactNode;
};

export const PuzzlesPageHeader = ({ tutorialSlot }: PuzzlesPageHeaderProps) => {
  return (
    <div className="relative mb-8 overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-primary/15 via-background to-background px-6 py-10 sm:px-10 sm:py-12">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 size-64 rounded-full bg-primary/20 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-20 -left-10 size-56 rounded-full bg-foreground/5 blur-3xl"
      />

      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground backdrop-blur">
            <Sparkles className="size-3.5 text-primary" />
            Logic arena
          </span>
          <h1 className="mt-4 flex items-center gap-3 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            <Zap className="size-9 text-primary sm:size-10" />
            <span className="bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
              Puzzles
            </span>
          </h1>
          <p className="mt-3 text-base text-muted-foreground sm:text-lg">
            Wire up logic gates, crack the riddles, and climb the leaderboard.
            Pick a puzzle below and start building.
          </p>
        </div>

        {tutorialSlot && <div className="shrink-0">{tutorialSlot}</div>}
      </div>
    </div>
  );
};
