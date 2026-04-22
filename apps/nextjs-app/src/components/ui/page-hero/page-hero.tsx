'use client';

import { Sparkles, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '@/utils/cn';

export type PageHeroProps = {
  badge?: string;
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  metaSlot?: ReactNode;
  rightSlot?: ReactNode;
  className?: string;
};

export const PageHero = ({
  badge,
  icon: Icon,
  title,
  description,
  metaSlot,
  rightSlot,
  className,
}: PageHeroProps) => {
  return (
    <div
      className={cn(
        'relative mb-8 overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-primary/15 via-background to-background px-6 py-10 sm:px-10 sm:py-12',
        className,
      )}
    >
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
          {badge && (
            <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground backdrop-blur">
              <Sparkles className="size-3.5 text-primary" />
              {badge}
            </span>
          )}
          <h1 className="mt-4 flex items-center gap-3 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            {Icon && <Icon className="size-9 text-primary sm:size-10" />}
            <span className="bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
              {title}
            </span>
          </h1>
          {description && (
            <div className="mt-3 text-base text-muted-foreground sm:text-lg">
              {description}
            </div>
          )}
          {metaSlot && <div className="mt-4">{metaSlot}</div>}
        </div>
        {rightSlot && <div className="shrink-0">{rightSlot}</div>}
      </div>
    </div>
  );
};
