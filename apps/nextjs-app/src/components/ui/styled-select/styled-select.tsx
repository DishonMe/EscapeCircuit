'use client';

import { Check, ChevronDown } from 'lucide-react';
import * as React from 'react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown/dropdown';
import { cn } from '@/utils/cn';

export type StyledSelectOption<T extends string | number> = {
  value: T;
  label: string;
  description?: string;
};

type StyledSelectProps<T extends string | number> = {
  value: T;
  onValueChange: (value: T) => void;
  options: ReadonlyArray<StyledSelectOption<T>>;
  'aria-label'?: string;
  placeholder?: string;
  id?: string;
  className?: string;
  contentClassName?: string;
  align?: 'start' | 'center' | 'end';
};

export function StyledSelect<T extends string | number>({
  value,
  onValueChange,
  options,
  placeholder,
  id,
  className,
  contentClassName,
  align = 'start',
  ...rest
}: StyledSelectProps<T>) {
  const selected = options.find((opt) => opt.value === value);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        id={id}
        aria-label={rest['aria-label']}
        className={cn(
          'inline-flex h-9 w-full items-center justify-between gap-2 rounded-lg border border-border bg-background px-3 text-[13px] text-foreground transition-colors',
          'hover:border-primary/40 hover:bg-secondary/30',
          'focus:outline-none focus:ring-1 focus:ring-ring',
          'data-[state=open]:border-primary/60 data-[state=open]:ring-1 data-[state=open]:ring-primary/40',
          className,
        )}
      >
        <span className={cn('truncate', !selected && 'text-muted-foreground')}>
          {selected?.label ?? placeholder ?? 'Select…'}
        </span>
        <ChevronDown
          aria-hidden
          className="size-4 shrink-0 text-muted-foreground transition-transform duration-150 data-[state=open]:rotate-180"
        />
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={align}
        sideOffset={6}
        className={cn(
          'min-w-[var(--radix-dropdown-menu-trigger-width)] overflow-hidden rounded-xl border border-border/70 bg-popover/95 p-1.5 shadow-xl backdrop-blur-md',
          contentClassName,
        )}
      >
        {options.map((opt) => {
          const isSelected = opt.value === value;
          return (
            <DropdownMenuItem
              key={String(opt.value)}
              onSelect={(e) => {
                e.preventDefault();
                onValueChange(opt.value);
              }}
              className={cn(
                'group flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] outline-none transition-colors',
                'focus:bg-primary/10 focus:text-foreground',
                'data-[highlighted]:bg-primary/10',
                isSelected && 'bg-primary/15 text-foreground',
              )}
            >
              <span
                className={cn(
                  'flex size-4 shrink-0 items-center justify-center rounded-full border text-primary transition-colors',
                  isSelected
                    ? 'border-primary bg-primary/20'
                    : 'border-border/70',
                )}
              >
                {isSelected && <Check className="size-3" strokeWidth={3} />}
              </span>
              <div className="flex min-w-0 flex-col">
                <span
                  className={cn(
                    'truncate font-medium',
                    isSelected ? 'text-foreground' : 'text-foreground/90',
                  )}
                >
                  {opt.label}
                </span>
                {opt.description && (
                  <span className="truncate text-[11px] text-muted-foreground">
                    {opt.description}
                  </span>
                )}
              </div>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
