'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Filter, X, AlertTriangle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { formatDate } from '@/utils/format';

import {
  useAdminPuzzles,
  AdminPuzzleFilters,
} from '../api/get-admin-puzzles';
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
                <span className="font-medium">
                  {entry.name || entry.title}
                </span>
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
                  className={`capitalize rounded-lg px-2 py-0.5 text-[11px] font-medium ${color}`}
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
              return (
                <span>{entry.creator?.username || 'Unknown'}</span>
              );
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
                        typeof ts === 'string'
                          ? new Date(ts).getTime()
                          : ts,
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
                <div className="flex gap-2 items-center">
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
          Filters{' '}
          {Object.values(filters).filter((v) => v).length > 0 &&
            `(${Object.values(filters).filter((v) => v).length})`}
        </Button>
        {Object.values(filters).filter((v) => v).length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="text-foreground/75"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel — always visible when toggled */}
      {showFilters && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Name Search */}
            <div>
              <label className="text-[13px] font-medium text-foreground">
                Name
              </label>
              <input
                type="text"
                placeholder="Search puzzle name..."
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] text-foreground focus:ring-1 focus:ring-ring focus:border-ring"
                value={filters.search || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setFilters({
                    ...filters,
                    search: e.target.value || undefined,
                  })
                }
              />
            </div>

            {/* Creator Username */}
            <div>
              <label className="text-[13px] font-medium text-foreground">
                Creator
              </label>
              <input
                type="text"
                placeholder="Search by creator username..."
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] text-foreground focus:ring-1 focus:ring-ring focus:border-ring"
                value={filters.creatorUsername || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setFilters({
                    ...filters,
                    creatorUsername: e.target.value || undefined,
                  })
                }
              />
            </div>

            {/* Status */}
            <div>
              <label className="text-[13px] font-medium text-foreground">
                Status
              </label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] text-foreground focus:ring-1 focus:ring-ring focus:border-ring"
                value={filters.status || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    status: (e.target.value || undefined) as any,
                  })
                }
              >
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="">All Statuses</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="draft">Draft</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="published">Published</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="unpublished">Unpublished</option>
              </select>
            </div>

            {/* Order By */}
            <div>
              <label className="text-[13px] font-medium text-foreground">
                Order By
              </label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] text-foreground focus:ring-1 focus:ring-ring focus:border-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    orderBy: e.target.value as any,
                  })
                }
              >
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="created_at">Created Date</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="name">Name</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="rating_count">Rating Count</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="avg_fun">Fun Rating</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="avg_clearness">Clearness Rating</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-[13px] font-medium text-foreground">
                Direction
              </label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] text-foreground focus:ring-1 focus:ring-ring focus:border-ring"
                value={filters.orderDirection || 'DESC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    orderDirection: e.target.value as any,
                  })
                }
              >
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="DESC">Descending</option>
                <option className="text-gray-900 bg-white dark:text-white dark:bg-gray-800" value="ASC">Ascending</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Content: loading / error / empty / table */}
      {renderContent()}
    </div>
  );
};
