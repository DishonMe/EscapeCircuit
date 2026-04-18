'use client';

import {
  ArrowDown,
  ArrowUp,
  Filter,
  LayoutGrid,
  List,
  Search,
  X,
} from 'lucide-react';
import { ChangeEvent, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';
import type { Meta } from '@/types/api';
import { cn } from '@/utils/cn';

import type { PuzzleFilters } from '../api/get-puzzles';
import type { ViewMode } from '../hooks/use-view-mode';

import { PuzzlesAdvancedFilters } from './puzzles-advanced-filters';

interface PuzzlesToolbarProps {
  filters: PuzzleFilters;
  onFiltersChange: (next: PuzzleFilters) => void;
  searchInput: string;
  onSearchInputChange: (s: string) => void;
  creatorInput: string;
  onCreatorInputChange: (s: string) => void;
  meta?: Meta;
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  activeFilterCount: number;
  onClearFilters: () => void;
  isRefetching: boolean;
}

// Detect a "simple" single-tier or all-tier difficulty selection
type DifficultyChip = 'all' | 'easy' | 'medium' | 'hard' | 'range';

function getDifficultyChip(selectedDifficulties?: number[]): DifficultyChip {
  if (!selectedDifficulties || selectedDifficulties.length === 0) return 'all';
  const sorted = [...selectedDifficulties].sort();
  if (
    sorted.length === 3 &&
    sorted[0] === 1 &&
    sorted[1] === 2 &&
    sorted[2] === 3
  )
    return 'all';
  if (sorted.length === 1) {
    if (sorted[0] === 1) return 'easy';
    if (sorted[0] === 2) return 'medium';
    if (sorted[0] === 3) return 'hard';
  }
  return 'range';
}

const CHIP_BASE =
  'rounded-full px-3 py-1 text-[12px] border border-border bg-background transition-colors hover:bg-secondary/40 aria-pressed:bg-secondary aria-pressed:ring-1 aria-pressed:ring-foreground/20';

export const PuzzlesToolbar = ({
  filters,
  onFiltersChange,
  searchInput,
  onSearchInputChange,
  creatorInput,
  onCreatorInputChange,
  meta,
  view,
  onViewChange,
  activeFilterCount,
  onClearFilters,
  isRefetching,
}: PuzzlesToolbarProps) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const advancedRef = useRef<HTMLDivElement>(null);

  const difficultyChip = getDifficultyChip(filters.selectedDifficulties);
  const medalFilter = filters.medalFilter ?? 'all';

  const showResultCount =
    meta !== undefined &&
    (medalFilter === 'all' || filters.medalFilter === undefined);

  const handleDifficultyChip = (chip: 'all' | 'easy' | 'medium' | 'hard') => {
    const map: Record<string, number[]> = {
      all: [1, 2, 3],
      easy: [1],
      medium: [2],
      hard: [3],
    };
    onFiltersChange({ ...filters, selectedDifficulties: map[chip], page: 1 });
  };

  const handleMedalChip = (
    medal: 'all' | 'unsolved' | 'bronze' | 'silver' | 'gold',
  ) => {
    onFiltersChange({ ...filters, medalFilter: medal, page: 1 });
  };

  const handleOrderByChange = (
    value: NonNullable<PuzzleFilters['orderBy']>,
  ) => {
    onFiltersChange({
      ...filters,
      orderBy: value,
      page: 1,
    });
  };

  const ORDER_BY_OPTIONS = [
    { value: 'created_at' as const, label: 'Newest' },
    { value: 'difficulty' as const, label: 'Difficulty' },
    { value: 'fun' as const, label: 'Fun' },
    { value: 'clearness' as const, label: 'Clearness' },
  ];

  const handleDirectionToggle = () => {
    const current = filters.orderDirection ?? 'ASC';
    onFiltersChange({
      ...filters,
      orderDirection: current === 'ASC' ? 'DESC' : 'ASC',
      page: 1,
    });
  };

  return (
    <div className="sticky top-14 z-20 border-b border-border bg-background">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-3">
        {/* Row 1: search, chips, sort, view toggle (pinned right) */}
        <div className="flex items-start gap-3">
          <div className="flex min-w-0 flex-1 flex-nowrap items-center gap-3 overflow-x-auto">
        {/* Search input */}
        <div className="relative shrink-0">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="text"
            placeholder="Search puzzles..."
            className="w-64 rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
            value={searchInput}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              onSearchInputChange(e.target.value);
              onFiltersChange({
                ...filters,
                search: e.target.value || undefined,
                page: 1,
              });
            }}
          />
        </div>

        {/* Result counter */}
        {showResultCount && (
          <span className="shrink-0 font-mono text-[12px] text-muted-foreground">
            {meta!.total} puzzles
          </span>
        )}

        <span
          aria-hidden
          className="h-6 w-px shrink-0 bg-border/70"
        />

        {/* Difficulty chip group */}
        <div
          role="group"
          aria-label="Filter by difficulty"
          className="flex shrink-0 flex-nowrap items-center gap-1.5"
        >
          <button
            type="button"
            aria-pressed={difficultyChip === 'all'}
            onClick={() => handleDifficultyChip('all')}
            className={CHIP_BASE}
          >
            All
          </button>
          <button
            type="button"
            aria-pressed={difficultyChip === 'easy'}
            onClick={() => handleDifficultyChip('easy')}
            className={CHIP_BASE}
          >
            Easy
          </button>
          <button
            type="button"
            aria-pressed={difficultyChip === 'medium'}
            onClick={() => handleDifficultyChip('medium')}
            className={CHIP_BASE}
          >
            Medium
          </button>
          <button
            type="button"
            aria-pressed={difficultyChip === 'hard'}
            onClick={() => handleDifficultyChip('hard')}
            className={CHIP_BASE}
          >
            Hard
          </button>
          {difficultyChip === 'range' && (
            <button
              type="button"
              aria-pressed={true}
              disabled
              className={cn(CHIP_BASE, 'cursor-default')}
            >
              Range
            </button>
          )}
        </div>

        <span
          aria-hidden
          className="h-6 w-px shrink-0 bg-border/70"
        />

        {/* Status chip group */}
        <div
          role="group"
          aria-label="Filter by status"
          className="flex shrink-0 flex-nowrap items-center gap-1.5"
        >
          {(
            [
              { value: 'all', label: 'All' },
              { value: 'unsolved', label: 'Unsolved' },
              { value: 'bronze', label: 'Bronze' },
              { value: 'silver', label: 'Silver' },
              { value: 'gold', label: 'Gold' },
            ] as const
          ).map((opt) => (
            <button
              key={opt.value}
              type="button"
              aria-pressed={medalFilter === opt.value}
              onClick={() => handleMedalChip(opt.value)}
              className={CHIP_BASE}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Sort select */}
        <StyledSelect
          aria-label="Sort by"
          className="puzzle-sort-dropdown w-[140px]"
          value={filters.orderBy ?? 'created_at'}
          onValueChange={handleOrderByChange}
          options={ORDER_BY_OPTIONS}
        />

        {/* Direction toggle */}
        <button
          type="button"
          onClick={handleDirectionToggle}
          aria-label={
            (filters.orderDirection ?? 'ASC') === 'ASC'
              ? 'Sort ascending — click to switch to descending'
              : 'Sort descending — click to switch to ascending'
          }
          className="inline-flex size-8 items-center justify-center rounded-lg border border-border bg-background text-foreground transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          {(filters.orderDirection ?? 'ASC') === 'ASC' ? (
            <ArrowUp className="size-4" />
          ) : (
            <ArrowDown className="size-4" />
          )}
        </button>

          </div>

        {/* View toggle — hidden on <sm, pinned to the far right of row 1 */}
        <div className="hidden shrink-0 items-center overflow-hidden rounded-lg border border-border sm:inline-flex">
          <button
            type="button"
            aria-pressed={view === 'gallery'}
            aria-label="Gallery view"
            onClick={() => onViewChange('gallery')}
            className={cn(
              'inline-flex size-8 items-center justify-center bg-background text-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
              view === 'gallery' && 'bg-secondary',
            )}
          >
            <LayoutGrid className="size-4" />
          </button>
          <button
            type="button"
            aria-pressed={view === 'list'}
            aria-label="List view"
            onClick={() => onViewChange('list')}
            className={cn(
              'inline-flex size-8 items-center justify-center bg-background text-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
              view === 'list' && 'bg-secondary',
            )}
          >
            <List className="size-4" />
          </button>
        </div>
        </div>

        {/* Row 2: More filters, Clear, Updating */}
        <div className="flex flex-wrap items-center gap-2">
          {/* More filters button */}
          <Button
            variant="outline"
            size="sm"
            className="puzzle-filters-button gap-2"
            onClick={() => setShowAdvanced((prev) => !prev)}
          >
            <Filter className="size-4" />
            More filters
            {activeFilterCount > 0 && (
              <span className="ml-0.5">({activeFilterCount})</span>
            )}
          </Button>

          {/* Clear button */}
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 text-[13px] text-muted-foreground"
              onClick={onClearFilters}
            >
              <X className="size-4" />
              Clear
            </Button>
          )}

          {/* Updating label */}
          {isRefetching && (
            <span className="ml-auto font-mono text-[12px] text-muted-foreground">
              Updating&hellip;
            </span>
          )}
        </div>
      </div>

      {/* Advanced filters panel — inline below toolbar */}
      {showAdvanced && (
        <div ref={advancedRef} className="mx-auto max-w-7xl px-4 pb-4">
          <PuzzlesAdvancedFilters
            filters={filters}
            onFiltersChange={onFiltersChange}
            creatorInput={creatorInput}
            onCreatorInputChange={onCreatorInputChange}
            onReset={() => {
              onClearFilters();
              setShowAdvanced(false);
            }}
          />
        </div>
      )}
    </div>
  );
};
