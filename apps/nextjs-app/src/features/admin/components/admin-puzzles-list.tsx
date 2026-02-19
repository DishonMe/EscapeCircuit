'use client';

import { useState, ChangeEvent } from 'react';
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

export const AdminPuzzlesList = () => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<AdminPuzzleFilters>({});

  const puzzlesQuery = useAdminPuzzles({ filters });

  const handleClearFilters = () => {
    setFilters({});
  };

  if (puzzlesQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (puzzlesQuery.isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Failed to load puzzles.{' '}
          {puzzlesQuery.error?.message &&
            `Error: ${puzzlesQuery.error.message}`}
        </p>
      </div>
    );
  }

  const puzzles = puzzlesQuery.data?.data || [];

  if (puzzles.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <p className="text-gray-600">No puzzles found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter Controls */}
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
            className="text-gray-600"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Name Search */}
            <div>
              <label className="text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                type="text"
                placeholder="Search puzzle name..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.search || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setFilters({
                    ...filters,
                    search: e.target.value || undefined,
                  })
                }
              />
            </div>

            {/* Status */}
            <div>
              <label className="text-sm font-medium text-gray-700">
                Status
              </label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.status || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    status: (e.target.value || undefined) as any,
                  })
                }
              >
                <option value="">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="unpublished">Unpublished</option>
              </select>
            </div>

            {/* Order By */}
            <div>
              <label className="text-sm font-medium text-gray-700">
                Order By
              </label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    orderBy: e.target.value as any,
                  })
                }
              >
                <option value="created_at">Created Date</option>
                <option value="name">Name</option>
                <option value="rating_count">Rating Count</option>
                <option value="avg_fun">Fun Rating</option>
                <option value="avg_clearness">Clearness Rating</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-sm font-medium text-gray-700">
                Direction
              </label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderDirection || 'DESC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setFilters({
                    ...filters,
                    orderDirection: e.target.value as any,
                  })
                }
              >
                <option value="DESC">Descending</option>
                <option value="ASC">Ascending</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Puzzles Table */}
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
                  ? 'text-green-600 bg-green-50'
                  : entry.status === 'draft'
                    ? 'text-yellow-600 bg-yellow-50'
                    : 'text-gray-500 bg-gray-50';
              return (
                <span
                  className={`capitalize rounded px-2 py-0.5 text-xs font-medium ${color}`}
                >
                  {entry.status}
                </span>
              );
            },
          },
          {
            title: 'Creator',
            field: 'creator_user_id',
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
                return <span className="text-gray-400">-</span>;
              return (
                <div className="flex flex-wrap gap-1">
                  {flags.map((f: string) => (
                    <span
                      key={f}
                      className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-xs text-red-700"
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
            field: 'created_at',
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
                <AdminDeletePuzzle
                  puzzleId={Number(entry.id)}
                  puzzleName={entry.name || entry.title || 'Unknown'}
                />
              );
            },
          },
        ]}
      />
    </div>
  );
};
