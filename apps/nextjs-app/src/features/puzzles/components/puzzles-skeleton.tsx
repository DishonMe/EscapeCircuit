'use client';

interface SkeletonProps {
  count?: number;
}

export const PuzzlesGallerySkeleton = ({ count = 9 }: SkeletonProps) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-border bg-card p-4 shadow-subtle animate-pulse min-h-[320px] flex flex-col gap-2.5"
          aria-hidden
        >
          {/* Top row: difficulty pill + save button */}
          <div className="flex items-center justify-between">
            <div className="h-5 w-16 rounded bg-secondary/50" />
            <div className="size-8 rounded-lg bg-secondary/50" />
          </div>

          {/* Title */}
          <div className="h-4 w-3/4 rounded bg-secondary/50" />
          <div className="h-4 w-1/2 rounded bg-secondary/50" />

          {/* Creator */}
          <div className="h-3 w-24 rounded bg-secondary/50" />

          {/* Description */}
          <div className="flex flex-col gap-1.5 min-h-[2.6em]">
            <div className="h-3 w-full rounded bg-secondary/50" />
            <div className="h-3 w-4/5 rounded bg-secondary/50" />
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-2">
            <div className="h-3 w-20 rounded bg-secondary/50" />
            <div className="h-3 w-14 rounded bg-secondary/50" />
          </div>

          {/* XP bar */}
          <div className="h-2 w-full rounded-full bg-secondary/50" />

          {/* Rating chips */}
          <div className="flex items-center gap-1.5">
            <div className="h-6 w-16 rounded-full bg-secondary/50" />
            <div className="h-6 w-14 rounded-full bg-secondary/50" />
            <div className="h-6 w-14 rounded-full bg-secondary/50" />
          </div>

          {/* Bottom action row */}
          <div className="mt-auto flex items-center justify-between pt-3">
            <div className="flex items-center gap-1">
              <div className="size-8 rounded-lg bg-secondary/50" />
              <div className="size-8 rounded-lg bg-secondary/50" />
            </div>
            <div className="h-7 w-16 rounded-md bg-secondary/50" />
          </div>
        </div>
      ))}
    </div>
  );
};

export const PuzzlesListSkeleton = ({ count = 9 }: SkeletonProps) => {
  return (
    <div className="divide-y divide-border rounded-xl border border-border bg-card overflow-hidden">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex h-14 items-center gap-4 border-b border-border px-4 animate-pulse"
          aria-hidden
        >
          {/* Status dot */}
          <div className="size-4 rounded-full bg-secondary/50 shrink-0" />

          {/* Title placeholder */}
          <div className="flex-1 h-4 rounded bg-secondary/50" />

          {/* Difficulty pill */}
          <div className="w-20 h-5 rounded bg-secondary/50 hidden sm:block" />

          {/* Rating chips */}
          <div className="hidden sm:flex items-center gap-1">
            <div className="w-14 h-5 rounded-full bg-secondary/50" />
            <div className="w-14 h-5 rounded-full bg-secondary/50" />
            <div className="w-14 h-5 rounded-full bg-secondary/50" />
          </div>

          {/* Save button */}
          <div className="size-8 rounded-lg bg-secondary/50 shrink-0" />

          {/* Kebab button */}
          <div className="size-8 rounded-lg bg-secondary/50 shrink-0" />
        </div>
      ))}
    </div>
  );
};
