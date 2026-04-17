'use client';

import { Trophy } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { RatingDialog } from '@/features/ratings/components/rating-dialog';
import { cn } from '@/utils/cn';

import { usePuzzles, PuzzleFilters } from '../api/get-puzzles';
import { useToggleSavePuzzle } from '../api/save-puzzle';
import { useDebouncedValue } from '../hooks/use-debounced-value';
import { useViewMode } from '../hooks/use-view-mode';

import { CreatorCommentDialog } from './creator-comment-dialog';
import { PuzzleCard } from './puzzle-card';
import { PuzzleDetailsDialog } from './puzzle-details-dialog';
import { PuzzleLeaderboard } from './puzzle-leaderboard';
import { PuzzleRow } from './puzzle-row';
import { PuzzlesActiveFilters } from './puzzles-active-filters';
import { PuzzlesEmpty } from './puzzles-empty';
import { PuzzlesPagination } from './puzzles-pagination';
import {
  PuzzlesGallerySkeleton,
  PuzzlesListSkeleton,
} from './puzzles-skeleton';
import { PuzzlesToolbar } from './puzzles-toolbar';

export const puzzlesTourSteps = [
  {
    target: '.puzzle-filters-button',
    content: 'You may filter by Puzzle Name, Creator, Difficulty, and more!',
    disableBeacon: true,
  },
  {
    target: '.puzzle-instructions-button',
    content:
      'Open the instructions to understand the puzzle goal, constraints, and any hints before you start solving.',
    scrollIntoView: true,
    scrollTarget: '.puzzle-card-action',
  },
  {
    target: '.dialog-close-button',
    content:
      'Use the Close button to exit the instructions and return to the puzzle list.',
    placement: 'bottom',
  },
  {
    target: '.puzzle-card-action',
    content: 'Click to start solving!',
  },
];

export const PuzzlesList = () => {
  // ── Dialog open-state ──────────────────────────────────────────────
  const [detailsPuzzleId, setDetailsPuzzleId] = useState<string | null>(null);
  const [commentPuzzleId, setCommentPuzzleId] = useState<string | null>(null);
  const [leaderboardPuzzleId, setLeaderboardPuzzleId] = useState<string | null>(
    null,
  );
  const [ratingPuzzleId, setRatingPuzzleId] = useState<string | null>(null);

  // ── Filter state ───────────────────────────────────────────────────
  const [filters, setFilters] = useState<PuzzleFilters>({
    page: 1,
    selectedDifficulties: [1, 2, 3],
  });
  const [creatorSearchInput, setCreatorSearchInput] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // ── View mode ──────────────────────────────────────────────────────
  const [view, setView] = useViewMode();

  // ── Debounced creator ──────────────────────────────────────────────
  const debouncedCreator = useDebouncedValue(creatorSearchInput, 400);

  useEffect(() => {
    setFilters((prev) => {
      const nextCreator = debouncedCreator.trim() || undefined;
      if (prev.creator === nextCreator) return prev;
      return { ...prev, creator: nextCreator, page: 1 };
    });
  }, [debouncedCreator]);

  // ── Server query ───────────────────────────────────────────────────
  const { data, isLoading, isFetching } = usePuzzles({
    filters: { page: filters.page || 1, ...filters },
    config: {
      placeholderData: (previousData) => previousData,
    },
  });

  const isRefetching = isFetching && !isLoading;
  const rawPuzzles = data?.data;
  const meta = data?.meta;

  const puzzles = useMemo(() => rawPuzzles ?? [], [rawPuzzles]);

  // ── Save mutation ──────────────────────────────────────────────────
  const saveMutation = useToggleSavePuzzle({});
  const savingPuzzleId = saveMutation.isPending
    ? (saveMutation.variables?.puzzleId ?? null)
    : null;

  // ── Medal client-side filter ───────────────────────────────────────
  const filteredPuzzles = useMemo(() => {
    if (!filters.medalFilter || filters.medalFilter === 'all') {
      return puzzles;
    }
    return puzzles.filter((p) => {
      const medal = p.best_medal ?? 0;
      switch (filters.medalFilter) {
        case 'unsolved':
          return medal === 0 || !p.is_solved;
        case 'bronze':
          return medal === 1;
        case 'silver':
          return medal === 2;
        case 'gold':
          return medal === 3;
        default:
          return true;
      }
    });
  }, [puzzles, filters.medalFilter]);

  // ── Active filter count ────────────────────────────────────────────
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (creatorSearchInput.trim()) count++;

    const diff = filters.selectedDifficulties;
    if (
      diff &&
      !(
        diff.length === 3 &&
        diff.includes(1) &&
        diff.includes(2) &&
        diff.includes(3)
      )
    ) {
      count++;
    }

    if (filters.minFun !== undefined) count++;
    if (filters.maxFun !== undefined) count++;
    if (filters.minClearness !== undefined) count++;
    if (filters.maxClearness !== undefined) count++;
    if (filters.medalFilter && filters.medalFilter !== 'all') count++;
    if (filters.experienceLevel && filters.experienceLevel !== 'all') count++;

    // Non-default order (default = created_at + ASC or no direction)
    const isDefaultOrder =
      (filters.orderBy === undefined || filters.orderBy === 'created_at') &&
      (filters.orderDirection === undefined ||
        filters.orderDirection === 'ASC');
    if (!isDefaultOrder) count++;

    if (filters.search && filters.search.trim()) count++;

    return count;
  }, [filters, creatorSearchInput]);

  // ── Dialog puzzle lookups ──────────────────────────────────────────
  const selectedPuzzle = useMemo(
    () =>
      detailsPuzzleId
        ? puzzles.find((p) => p.id === detailsPuzzleId)
        : undefined,
    [detailsPuzzleId, puzzles],
  );

  const selectedCommentPuzzle = useMemo(
    () =>
      commentPuzzleId
        ? puzzles.find((p) => p.id === commentPuzzleId)
        : undefined,
    [commentPuzzleId, puzzles],
  );

  const selectedLeaderboardPuzzle = useMemo(
    () =>
      leaderboardPuzzleId
        ? puzzles.find((p) => p.id === leaderboardPuzzleId)
        : undefined,
    [leaderboardPuzzleId, puzzles],
  );

  // ── Handlers ───────────────────────────────────────────────────────
  const handleClearFilters = () => {
    setFilters({ page: 1, selectedDifficulties: [1, 2, 3] });
    setCreatorSearchInput('');
    setSearchInput('');
  };

  const handleSave = (puzzleId: string) => {
    saveMutation.mutate({ puzzleId });
  };

  const handleRate = (puzzleId: string) => setRatingPuzzleId(puzzleId);
  const handleInstructions = (puzzleId: string) => setDetailsPuzzleId(puzzleId);
  const handleComment = (puzzleId: string) => setCommentPuzzleId(puzzleId);
  const handleLeaderboard = (puzzleId: string) =>
    setLeaderboardPuzzleId(puzzleId);

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <>
      <PuzzlesToolbar
        filters={filters}
        onFiltersChange={setFilters}
        searchInput={searchInput}
        onSearchInputChange={setSearchInput}
        creatorInput={creatorSearchInput}
        onCreatorInputChange={setCreatorSearchInput}
        meta={meta}
        view={view}
        onViewChange={setView}
        activeFilterCount={activeFilterCount}
        onClearFilters={handleClearFilters}
        isRefetching={isRefetching}
      />

      <div className="mx-auto max-w-7xl px-4 pt-6">
        <PuzzlesActiveFilters
          filters={filters}
          creatorInput={creatorSearchInput}
          onFiltersChange={setFilters}
          onClearCreator={() => setCreatorSearchInput('')}
          onClearAll={handleClearFilters}
        />

        {/* Initial loading skeletons */}
        {isLoading &&
          !data &&
          (view === 'gallery' ? (
            <PuzzlesGallerySkeleton />
          ) : (
            <PuzzlesListSkeleton />
          ))}

        {/* Empty state */}
        {!isLoading && filteredPuzzles.length === 0 && (
          <PuzzlesEmpty
            hasActiveFilters={activeFilterCount > 0}
            onClearFilters={handleClearFilters}
          />
        )}

        {/* Gallery view */}
        {filteredPuzzles.length > 0 && view === 'gallery' && (
          <div
            className={cn(
              'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3',
              isRefetching && 'opacity-80 transition-opacity',
            )}
          >
            {filteredPuzzles.map((puzzle) => (
              <PuzzleCard
                key={puzzle.id}
                puzzle={puzzle}
                onRate={handleRate}
                onInstructions={handleInstructions}
                onComment={handleComment}
                onLeaderboard={handleLeaderboard}
                onSave={handleSave}
                savingPuzzleId={savingPuzzleId}
              />
            ))}
          </div>
        )}

        {/* List view */}
        {filteredPuzzles.length > 0 && view === 'list' && (
          <div
            className={cn(
              'divide-y divide-border overflow-hidden rounded-xl border border-border bg-card',
              isRefetching && 'opacity-80 transition-opacity',
            )}
          >
            {filteredPuzzles.map((puzzle) => (
              <PuzzleRow
                key={puzzle.id}
                puzzle={puzzle}
                onRate={handleRate}
                onInstructions={handleInstructions}
                onComment={handleComment}
                onLeaderboard={handleLeaderboard}
                onSave={handleSave}
                savingPuzzleId={savingPuzzleId}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {meta && meta.totalPages > 1 && (
          <PuzzlesPagination
            page={filters.page ?? 1}
            totalPages={meta.totalPages}
            total={meta.total}
            pageSize={9}
            filteredCountOnPage={filteredPuzzles.length}
            medalFilter={filters.medalFilter ?? 'all'}
            onPageChange={(page) => setFilters({ ...filters, page })}
          />
        )}
      </div>

      {/* Dialogs */}
      <PuzzleDetailsDialog
        puzzle={selectedPuzzle}
        open={Boolean(selectedPuzzle)}
        onOpenChange={(open) => {
          if (!open) setDetailsPuzzleId(null);
        }}
        showLink={true}
      />

      <CreatorCommentDialog
        puzzle={selectedCommentPuzzle}
        open={Boolean(selectedCommentPuzzle)}
        onOpenChange={(open) => {
          if (!open) setCommentPuzzleId(null);
        }}
        showLink={true}
      />

      {leaderboardPuzzleId && selectedLeaderboardPuzzle && (
        <Dialog
          open={true}
          onOpenChange={(open) => {
            if (!open) setLeaderboardPuzzleId(null);
          }}
        >
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Trophy className="size-5 text-amber-500" />
                Leaderboard
              </DialogTitle>
              <DialogDescription>Top solvers for this puzzle</DialogDescription>
            </DialogHeader>
            <div className="max-h-[60vh] overflow-y-auto">
              <PuzzleLeaderboard puzzleId={selectedLeaderboardPuzzle.id} />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setLeaderboardPuzzleId(null)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {ratingPuzzleId && (
        <RatingDialog
          puzzleId={ratingPuzzleId}
          open={true}
          onOpenChange={(open) => {
            if (!open) setRatingPuzzleId(null);
          }}
        />
      )}

    </>
  );
};
