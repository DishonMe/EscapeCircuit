'use client';

import { X } from 'lucide-react';
import { ChangeEvent } from 'react';

import { Button } from '@/components/ui/button';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';
import { cn } from '@/utils/cn';

import type { PuzzleFilters } from '../api/get-puzzles';

interface PuzzlesAdvancedFiltersProps {
  filters: PuzzleFilters;
  onFiltersChange: (next: PuzzleFilters) => void;
  creatorInput: string;
  onCreatorInputChange: (s: string) => void;
  onReset?: () => void;
}

const FIELD_LABEL =
  'mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground';
const FIELD_INPUT =
  'w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring';

const DIFFICULTY_OPTIONS = [
  { value: 1, label: 'Easy' },
  { value: 2, label: 'Medium' },
  { value: 3, label: 'Hard' },
];

function getFrom(selectedDifficulties?: number[]): number {
  if (!selectedDifficulties || selectedDifficulties.length === 0) return 1;
  return Math.min(...selectedDifficulties);
}

function getTo(selectedDifficulties?: number[]): number {
  if (!selectedDifficulties || selectedDifficulties.length === 0) return 3;
  return Math.max(...selectedDifficulties);
}

function buildRange(from: number, to: number): number[] {
  const result: number[] = [];
  for (let i = from; i <= to; i++) {
    result.push(i);
  }
  return result;
}

export const PuzzlesAdvancedFilters = ({
  filters,
  onFiltersChange,
  creatorInput,
  onCreatorInputChange,
  onReset,
}: PuzzlesAdvancedFiltersProps) => {
  const from = getFrom(filters.selectedDifficulties);
  const to = getTo(filters.selectedDifficulties);

  const handleFromChange = (newFrom: number) => {
    const newTo = newFrom > to ? newFrom : to;
    onFiltersChange({
      ...filters,
      selectedDifficulties: buildRange(newFrom, newTo),
      page: 1,
    });
  };

  const handleToChange = (newTo: number) => {
    const newFrom = newTo < from ? newTo : from;
    onFiltersChange({
      ...filters,
      selectedDifficulties: buildRange(newFrom, newTo),
      page: 1,
    });
  };

  const handleReset = () => {
    if (onReset) {
      onReset();
    } else {
      onFiltersChange({ page: 1, selectedDifficulties: [1, 2, 3] });
      onCreatorInputChange('');
    }
  };

  const experienceLevel = filters.experienceLevel ?? 'all';

  return (
    <div className="space-y-5 rounded-xl border border-border bg-card p-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Creator */}
        <div>
          <label htmlFor="adv-creator" className={FIELD_LABEL}>
            Creator
          </label>
          <input
            id="adv-creator"
            type="text"
            placeholder="Search by creator..."
            className={FIELD_INPUT}
            value={creatorInput}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              onCreatorInputChange(e.target.value)
            }
          />
        </div>

        {/* Difficulty Range */}
        <div>
          <span className={FIELD_LABEL}>Difficulty Range</span>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label htmlFor="adv-diff-from" className="sr-only">
                From
              </label>
              <StyledSelect
                id="adv-diff-from"
                aria-label="Difficulty range from"
                value={from}
                onValueChange={handleFromChange}
                options={DIFFICULTY_OPTIONS}
              />
            </div>
            <span className="shrink-0 text-[12px] text-muted-foreground">
              to
            </span>
            <div className="flex-1">
              <label htmlFor="adv-diff-to" className="sr-only">
                To
              </label>
              <StyledSelect
                id="adv-diff-to"
                aria-label="Difficulty range to"
                value={to}
                onValueChange={handleToChange}
                options={DIFFICULTY_OPTIONS}
              />
            </div>
          </div>
        </div>

        {/* Fun Range */}
        <div>
          <span className={FIELD_LABEL}>Fun Rating</span>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label htmlFor="adv-fun-min" className="sr-only">
                Min Fun
              </label>
              <input
                id="adv-fun-min"
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="Min"
                className={FIELD_INPUT}
                value={filters.minFun ?? ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  onFiltersChange({
                    ...filters,
                    minFun: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                    page: 1,
                  })
                }
              />
            </div>
            <span className="shrink-0 text-[12px] text-muted-foreground">
              &ndash;
            </span>
            <div className="flex-1">
              <label htmlFor="adv-fun-max" className="sr-only">
                Max Fun
              </label>
              <input
                id="adv-fun-max"
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="Max"
                className={FIELD_INPUT}
                value={filters.maxFun ?? ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  onFiltersChange({
                    ...filters,
                    maxFun: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                    page: 1,
                  })
                }
              />
            </div>
          </div>
        </div>

        {/* Clearness Range */}
        <div>
          <span className={FIELD_LABEL}>Clearness Rating</span>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label htmlFor="adv-clearness-min" className="sr-only">
                Min Clearness
              </label>
              <input
                id="adv-clearness-min"
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="Min"
                className={FIELD_INPUT}
                value={filters.minClearness ?? ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  onFiltersChange({
                    ...filters,
                    minClearness: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                    page: 1,
                  })
                }
              />
            </div>
            <span className="shrink-0 text-[12px] text-muted-foreground">
              &ndash;
            </span>
            <div className="flex-1">
              <label htmlFor="adv-clearness-max" className="sr-only">
                Max Clearness
              </label>
              <input
                id="adv-clearness-max"
                type="number"
                min="0"
                max="5"
                step="0.5"
                placeholder="Max"
                className={FIELD_INPUT}
                value={filters.maxClearness ?? ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  onFiltersChange({
                    ...filters,
                    maxClearness: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                    page: 1,
                  })
                }
              />
            </div>
          </div>
        </div>

        {/* Experience Level */}
        <div className="md:col-span-2">
          <span className={FIELD_LABEL}>Experience Level</span>
          <div
            role="group"
            aria-label="Experience level filter"
            className="flex flex-wrap items-center gap-2"
          >
            {(
              [
                { value: 'all', label: 'All' },
                { value: 'experienced', label: 'Experienced' },
                { value: 'inexperienced', label: 'Inexperienced' },
              ] as const
            ).map((opt) => (
              <button
                key={opt.value}
                type="button"
                aria-pressed={experienceLevel === opt.value}
                onClick={() =>
                  onFiltersChange({
                    ...filters,
                    experienceLevel: opt.value,
                    page: 1,
                  })
                }
                className={cn(
                  'rounded-full border border-border bg-background px-3 py-1 text-[12px] transition-colors',
                  'hover:bg-secondary/40',
                  'aria-pressed:bg-secondary aria-pressed:ring-1 aria-pressed:ring-foreground/20',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Reset */}
      <div className="flex justify-start border-t border-border pt-4">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 text-[13px] text-muted-foreground"
          onClick={handleReset}
        >
          <X className="size-4" />
          Reset all filters
        </Button>
      </div>
    </div>
  );
};
