'use client';

import { X } from 'lucide-react';

import type { PuzzleFilters } from '../api/get-puzzles';

interface PuzzlesActiveFiltersProps {
  filters: PuzzleFilters;
  creatorInput: string;
  onFiltersChange: (next: PuzzleFilters) => void;
  onClearCreator: () => void;
  onClearAll: () => void;
}

const CHIP_CLASS =
  'inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-border bg-secondary/30 px-3 py-1 text-[12px] text-foreground transition-colors hover:bg-secondary/60';

function isDefaultDifficulties(selectedDifficulties?: number[]): boolean {
  if (!selectedDifficulties) return true;
  const sorted = [...selectedDifficulties].sort();
  return (
    sorted.length === 3 && sorted[0] === 1 && sorted[1] === 2 && sorted[2] === 3
  );
}

function difficultyLabel(selectedDifficulties: number[]): string {
  const sorted = [...selectedDifficulties].sort();
  const names: Record<number, string> = { 1: 'Easy', 2: 'Medium', 3: 'Hard' };
  if (sorted.length === 1) return names[sorted[0]] ?? String(sorted[0]);
  const from = names[sorted[0]] ?? String(sorted[0]);
  const lastIdx = sorted.length - 1;
  const to = names[sorted[lastIdx]] ?? String(sorted[lastIdx]);
  return `${from} \u2013 ${to}`;
}

function orderLabel(
  orderBy: PuzzleFilters['orderBy'],
  orderDirection: PuzzleFilters['orderDirection'],
): string {
  const byMap: Record<string, string> = {
    created_at: 'Newest',
    difficulty: 'Difficulty',
    fun: 'Fun',
    clearness: 'Clearness',
  };
  const by = byMap[orderBy ?? 'created_at'] ?? orderBy ?? 'Newest';
  const dir = (orderDirection ?? 'ASC') === 'DESC' ? '\u2193' : '\u2191';
  return `${by} ${dir}`;
}

export const PuzzlesActiveFilters = ({
  filters,
  creatorInput,
  onFiltersChange,
  onClearCreator,
  onClearAll,
}: PuzzlesActiveFiltersProps) => {
  const chips: React.ReactNode[] = [];

  // Creator
  if (creatorInput.trim()) {
    chips.push(
      <button
        key="creator"
        type="button"
        className={CHIP_CLASS}
        onClick={() => {
          onClearCreator();
          onFiltersChange({ ...filters, creator: undefined, page: 1 });
        }}
        aria-label={`Remove creator filter: ${creatorInput}`}
      >
        <X className="size-3" aria-hidden />
        Creator: {creatorInput}
      </button>,
    );
  }

  // Difficulty (non-default)
  if (
    filters.selectedDifficulties &&
    !isDefaultDifficulties(filters.selectedDifficulties)
  ) {
    chips.push(
      <button
        key="difficulty"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({
            ...filters,
            selectedDifficulties: [1, 2, 3],
            page: 1,
          })
        }
        aria-label="Remove difficulty filter"
      >
        <X className="size-3" aria-hidden />
        Difficulty: {difficultyLabel(filters.selectedDifficulties)}
      </button>,
    );
  }

  // Min Fun
  if (filters.minFun !== undefined) {
    chips.push(
      <button
        key="minFun"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, minFun: undefined, page: 1 })
        }
        aria-label="Remove min fun filter"
      >
        <X className="size-3" aria-hidden />
        Fun &ge; {filters.minFun.toFixed(1)}
      </button>,
    );
  }

  // Max Fun
  if (filters.maxFun !== undefined) {
    chips.push(
      <button
        key="maxFun"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, maxFun: undefined, page: 1 })
        }
        aria-label="Remove max fun filter"
      >
        <X className="size-3" aria-hidden />
        Fun &le; {filters.maxFun.toFixed(1)}
      </button>,
    );
  }

  // Min Clearness
  if (filters.minClearness !== undefined) {
    chips.push(
      <button
        key="minClearness"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, minClearness: undefined, page: 1 })
        }
        aria-label="Remove min clearness filter"
      >
        <X className="size-3" aria-hidden />
        Clearness &ge; {filters.minClearness.toFixed(1)}
      </button>,
    );
  }

  // Max Clearness
  if (filters.maxClearness !== undefined) {
    chips.push(
      <button
        key="maxClearness"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, maxClearness: undefined, page: 1 })
        }
        aria-label="Remove max clearness filter"
      >
        <X className="size-3" aria-hidden />
        Clearness &le; {filters.maxClearness.toFixed(1)}
      </button>,
    );
  }

  // Order (non-default: not created_at ASC)
  const isDefaultOrder =
    (filters.orderBy === undefined || filters.orderBy === 'created_at') &&
    (filters.orderDirection === undefined || filters.orderDirection === 'ASC');
  if (!isDefaultOrder) {
    chips.push(
      <button
        key="order"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({
            ...filters,
            orderBy: undefined,
            orderDirection: undefined,
            page: 1,
          })
        }
        aria-label="Remove sort filter"
      >
        <X className="size-3" aria-hidden />
        Order: {orderLabel(filters.orderBy, filters.orderDirection)}
      </button>,
    );
  }

  // Experience level (non-default)
  if (filters.experienceLevel && filters.experienceLevel !== 'all') {
    const label =
      filters.experienceLevel === 'experienced'
        ? 'Experienced'
        : 'Inexperienced';
    chips.push(
      <button
        key="experienceLevel"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, experienceLevel: 'all', page: 1 })
        }
        aria-label="Remove experience level filter"
      >
        <X className="size-3" aria-hidden />
        Experience: {label}
      </button>,
    );
  }

  // Medal filter (non-default)
  if (filters.medalFilter && filters.medalFilter !== 'all') {
    const medalMap: Record<string, string> = {
      unsolved: 'Unsolved',
      bronze: 'Bronze',
      silver: 'Silver',
      gold: 'Gold',
    };
    const label = medalMap[filters.medalFilter] ?? filters.medalFilter;
    chips.push(
      <button
        key="medal"
        type="button"
        className={CHIP_CLASS}
        onClick={() =>
          onFiltersChange({ ...filters, medalFilter: 'all', page: 1 })
        }
        aria-label="Remove status filter"
      >
        <X className="size-3" aria-hidden />
        Status: {label}
      </button>,
    );
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 px-0 py-2">
      {chips}
      <button
        type="button"
        onClick={onClearAll}
        className="ml-1 text-[12px] text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
      >
        Clear all
      </button>
    </div>
  );
};
