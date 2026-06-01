'use client';

import {
  Filter,
  X,
  AlertTriangle,
  Eye,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { useState, useEffect, ChangeEvent } from 'react';

// eslint-disable-next-line import/no-restricted-paths -- shared puzzle preview dialog currently lives under app/; extracting it is a separate refactor.
import { PuzzleViewDialog } from '@/app/app/my-puzzles/_components/puzzle-view-dialog';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';
import { Table } from '@/components/ui/table';
import { formatDate } from '@/utils/format';

import { useAdminPuzzles, AdminPuzzleFilters } from '../api/get-admin-puzzles';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
  { value: 'unpublished', label: 'Unpublished' },
] as const;

const PUZZLE_ORDER_BY_OPTIONS = [
  { value: 'created_at', label: 'Created Date' },
  { value: 'name', label: 'Name' },
  { value: 'rating_count', label: 'Rating Count' },
  { value: 'avg_fun', label: 'Fun Rating' },
  { value: 'avg_clearness', label: 'Clearness Rating' },
] as const;
import { AdminDeletePuzzle } from './admin-delete-puzzle';
import { AdminUnpublishPuzzle } from './admin-unpublish-puzzle';

// Debounce hook — delays value updates until user stops typing
function useDebouncedValue<T>(value: T, delay: number = 400): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export const AdminPuzzlesList = () => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<AdminPuzzleFilters>({});
  const [previewPuzzle, setPreviewPuzzle] = useState<any | null>(null);
  const activeFilterCount = Object.values(filters).filter((v) => v).length;

  // Debounce text inputs so the API isn't called on every keystroke
  const debouncedFilters = useDebouncedValue(filters);

  const puzzlesQuery = useAdminPuzzles({ filters: debouncedFilters });

  const handleClearFilters = () => {
    setFilters({});
  };

  const puzzles = puzzlesQuery.data?.data || [];

  // Render content below filters based on query state
  const renderContent = () => {
    if (puzzlesQuery.isLoading) {
      return (
        <div className="flex h-48 w-full items-center justify-center">
          <Spinner size="lg" />
        </div>
      );
    }

    if (puzzlesQuery.isError) {
      return (
        <div className="rounded-lg border border-red-200/60 bg-red-50/50 p-4">
          <p className="text-[13px] text-red-700">
            Failed to load puzzles.{' '}
            {puzzlesQuery.error?.message &&
              `Error: ${puzzlesQuery.error.message}`}
          </p>
        </div>
      );
    }

    if (puzzles.length === 0) {
      return (
        <div className="rounded-xl border border-border bg-secondary p-4">
          <p className="text-foreground/80">No puzzles found.</p>
        </div>
      );
    }

    return (
      <Table
        data={puzzles}
        columns={[
          {
            title: 'Name',
            field: 'name',
            Cell({ entry }: { entry: any }) {
              return (
                <span className="font-medium">{entry.name || entry.title}</span>
              );
            },
          },
          {
            title: 'Status',
            field: 'status',
            Cell({ entry }: { entry: any }) {
              const color =
                entry.status === 'published'
                  ? 'text-emerald-700 bg-emerald-50/50'
                  : entry.status === 'draft'
                    ? 'text-amber-700 bg-amber-50/50'
                    : 'text-foreground/80 bg-secondary';
              return (
                <span
                  className={`rounded-lg px-2 py-0.5 text-[11px] font-medium capitalize ${color}`}
                >
                  {entry.status}
                </span>
              );
            },
          },
          {
            title: 'Creator',
            field: 'creator' as any,
            Cell({ entry }: { entry: any }) {
              return <span>{entry.creator?.username || 'Unknown'}</span>;
            },
          },
          {
            title: 'Ratings',
            field: 'rating_count',
          },
          {
            title: 'Flags',
            field: 'id',
            Cell({ entry }: { entry: any }) {
              const flags: string[] = entry.flags || [];
              if (flags.length === 0)
                return <span className="text-foreground/70">-</span>;
              return (
                <div className="flex flex-wrap gap-1">
                  {flags.map((f: string) => (
                    <span
                      key={f}
                      className="inline-flex items-center gap-1 rounded-lg bg-red-50/50 px-2 py-0.5 text-[11px] text-red-700"
                    >
                      <AlertTriangle className="size-3" />{' '}
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              );
            },
          },
          {
            title: 'Created',
            field: 'createdAt',
            Cell({ entry }: { entry: any }) {
              const ts = entry.created_at || entry.createdAt;
              return (
                <span>
                  {ts
                    ? formatDate(
                        typeof ts === 'string' ? new Date(ts).getTime() : ts,
                      )
                    : '-'}
                </span>
              );
            },
          },
          {
            title: '',
            field: 'id',
            Cell({ entry }: { entry: any }) {
              return (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPreviewPuzzle(entry)}
                  >
                    <Eye className="mr-1 size-4" />
                    Preview
                  </Button>
                  {entry.status === 'published' ? (
                    <AdminUnpublishPuzzle
                      puzzleId={Number(entry.id)}
                      puzzleName={entry.name || entry.title || 'Unknown'}
                    />
                  ) : (
                    <AdminDeletePuzzle
                      puzzleId={Number(entry.id)}
                      puzzleName={entry.name || entry.title || 'Unknown'}
                    />
                  )}

                  <PuzzleViewDialog
                    puzzle={previewPuzzle}
                    open={!!previewPuzzle}
                    onOpenChange={(open) => {
                      if (!open) setPreviewPuzzle(null);
                    }}
                  />
                </div>
              );
            },
          },
        ]}
      />
    );
  };

  return (
    <div className="space-y-4">
      {/* Filter Controls — always visible */}
      <div className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className="gap-2"
        >
          <Filter className="size-4" />
          Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
        </Button>
        {activeFilterCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="text-[13px] text-muted-foreground"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel — always visible when toggled */}
      {showFilters && (
        <div className="space-y-5 rounded-xl border border-border bg-card p-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Name Search */}
            <label className="flex flex-col">
              <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Name
              </span>
              <input
                type="text"
                placeholder="Search puzzle name..."
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.search || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setFilters({
                    ...filters,
                    search: e.target.value || undefined,
                  })
                }
              />
            </label>

            {/* Creator Username */}
            <label className="flex flex-col">
              <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Creator
              </span>
              <input
                type="text"
                placeholder="Search by creator username..."
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.creatorUsername || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setFilters({
                    ...filters,
                    creatorUsername: e.target.value || undefined,
                  })
                }
              />
            </label>

            {/* Status */}
            <label className="flex flex-col">
              <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Status
              </span>
              <StyledSelect
                aria-label="Status"
                value={filters.status || ''}
                onValueChange={(v) =>
                  setFilters({
                    ...filters,
                    status: (v || undefined) as any,
                  })
                }
                options={STATUS_OPTIONS}
              />
            </label>

            {/* Order By */}
            <label className="flex flex-col">
              <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Order By
              </span>
              <StyledSelect
                aria-label="Order by"
                value={filters.orderBy || 'created_at'}
                onValueChange={(v) =>
                  setFilters({ ...filters, orderBy: v as any })
                }
                options={PUZZLE_ORDER_BY_OPTIONS}
              />
            </label>

            {/* Direction */}
            <label className="flex flex-col">
              <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Direction
              </span>
              <button
                type="button"
                onClick={() => {
                  const currentDirection = filters.orderDirection || 'DESC';
                  const newDirection =
                    currentDirection === 'ASC' ? 'DESC' : 'ASC';
                  setFilters({
                    ...filters,
                    orderDirection: newDirection as any,
                  });
                }}
                className="inline-flex h-9 w-full items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-border bg-background px-3 text-[13px] text-foreground transition-colors hover:border-primary/40 hover:bg-secondary/30 focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {(filters.orderDirection || 'DESC') === 'ASC' ? (
                  <>
                    <ArrowUp className="size-4" />
                    <span>Ascending</span>
                  </>
                ) : (
                  <>
                    <ArrowDown className="size-4" />
                    <span>Descending</span>
                  </>
                )}
              </button>
            </label>
          </div>
        </div>
      )}

      {/* Content: loading / error / empty / table */}
      {renderContent()}
    </div>
  );
};
