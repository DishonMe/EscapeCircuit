'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Filter, X, ArrowUp, ArrowDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { formatDate } from '@/utils/format';

import { useUsers, UserFilters } from '../api/get-users';

import { DeleteUser } from './delete-user';
import { AssignCreatorButton } from '@/features/admin/components/assign-creator-button';
import { RemoveCreatorButton } from '@/features/admin/components/remove-creator-button';
import { CreatorPuzzleLimits } from '@/features/admin/components/creator-puzzle-limits';

// Debounce hook — delays value updates until user stops typing
function useDebouncedValue<T>(value: T, delay: number = 400): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export const UsersList = () => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<UserFilters>({});
  const activeFilterCount = Object.values(filters).filter((v) => v).length;

  // Debounce text inputs so the API isn't called on every keystroke
  const debouncedFilters = useDebouncedValue(filters);

  const usersQuery = useUsers({ filters: debouncedFilters });

  const handleClearFilters = () => {
    setFilters({});
  };

  // The API returns { data: User[] } or just User[]
  const users = usersQuery.data
    ? Array.isArray(usersQuery.data)
      ? usersQuery.data
      : usersQuery.data?.data
    : [];

  // Render content below filters based on query state
  const renderContent = () => {
    if (usersQuery.isLoading) {
      return (
        <div className="flex h-48 w-full items-center justify-center">
          <Spinner size="lg" />
        </div>
      );
    }

    if (usersQuery.isError) {
      return (
        <div className="rounded-xl border border-red-200/60 bg-red-50/50 p-4">
          <p className="text-[13px] text-red-700">
            Failed to load users. {usersQuery.error?.message && `Error: ${usersQuery.error.message}`}
          </p>
        </div>
      );
    }

    if (!users || users.length === 0) {
      return (
        <div className="rounded-xl border border-border bg-secondary/50 p-4">
          <p className="text-[13px] text-foreground/80">No users found.</p>
        </div>
      );
    }

    return (
      <Table
        data={users}
        columns={[
          {
            title: 'Username',
            field: 'username',
          },
          {
            title: 'Email',
            field: 'email',
          },
          {
            title: 'Role',
            field: 'role',
            Cell({ entry: { role } }: { entry: any }) {
              const roleColors: Record<string, string> = {
                admin: 'bg-violet-50/50 text-violet-700',
                creator: 'bg-emerald-50/50 text-emerald-700',
                solver: 'bg-secondary text-foreground/80',
                pending_creator: 'bg-amber-50/50 text-amber-700',
              };
              const color = roleColors[role] || 'bg-secondary text-foreground/80';
              const label = role === 'pending_creator' ? 'Pending Creator' : role;
              return (
                <span className={`capitalize rounded-md px-2 py-0.5 text-[11px] font-medium ${color}`}>
                  {label}
                </span>
              );
            },
          },
          {
            title: 'Created At',
            field: 'createdAt',
            Cell({ entry: { createdAt } }: { entry: any }) {
              return <span>{formatDate(createdAt)}</span>;
            },
          },
          {
            title: 'Actions',
            field: 'id',
            Cell({ entry }: { entry: any }) {
              return (
                <div className="flex gap-2 items-center">
                  {entry.role === 'solver' && (
                    <AssignCreatorButton
                      userId={Number(entry.id)}
                      username={entry.username}
                    />
                  )}
                  {(entry.role === 'creator' || entry.role === 'pending_creator') && (
                    <>
                      <RemoveCreatorButton
                        userId={Number(entry.id)}
                        username={entry.username}
                        currentRole={entry.role}
                      />
                      {entry.role === 'creator' && (
                        <CreatorPuzzleLimits
                          userId={Number(entry.id)}
                          username={entry.username}
                          effectiveMaxPublished={entry.effective_max_published ?? 5}
                          effectiveMaxUnpublished={entry.effective_max_unpublished ?? 5}
                          maxPublishedOverride={entry.max_published_override ?? null}
                          maxUnpublishedOverride={entry.max_unpublished_override ?? null}
                        />
                      )}
                    </>
                  )}
                  <DeleteUser id={entry.id} />
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
            className="text-muted-foreground text-[13px]"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel — always visible when toggled */}
      {showFilters && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Username Search */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Username</label>
              <input
                type="text"
                placeholder="Search username..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.usernameSearch || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, usernameSearch: e.target.value || undefined })}
              />
            </div>

            {/* Role */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Role</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.role || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, role: (e.target.value || undefined) as any })}
              >
                <option className="text-foreground bg-card" value="">All Roles</option>
                <option className="text-foreground bg-card" value="solver">Solver</option>
                <option className="text-foreground bg-card" value="creator">Creator</option>
                <option className="text-foreground bg-card" value="pending_creator">Pending Creator</option>
                <option className="text-foreground bg-card" value="admin">Admin</option>
              </select>
            </div>

            {/* Experience Level */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Experience</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.experienceLevel || 'all'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, experienceLevel: e.target.value as any })}
              >
                <option className="text-foreground bg-card" value="all">All</option>
                <option className="text-foreground bg-card" value="experienced">Experienced (Lvl 5+)</option>
                <option className="text-foreground bg-card" value="inexperienced">Inexperienced (Lvl 1-4)</option>
              </select>
            </div>

            {/* Order By */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Order By</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any })}
              >
                <option className="text-foreground bg-card" value="created_at">Creation Date</option>
                <option className="text-foreground bg-card" value="level">Level</option>
                <option className="text-foreground bg-card" value="experienced">Experienced Status</option>
                <option className="text-foreground bg-card" value="role">Role</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Direction</label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const currentDirection = filters.orderDirection || 'ASC';
                  const newDirection = currentDirection === 'ASC' ? 'DESC' : 'ASC';
                  setFilters({ ...filters, orderDirection: newDirection as any });
                }}
                className="gap-1 px-2 py-1 inline-flex items-center whitespace-nowrap"
              >
                {(filters.orderDirection || 'ASC') === 'ASC' ? (
                  <>
                    <ArrowUp className="size-3 inline-block" />
                    <span> Ascending</span>
                  </>
                ) : (
                  <>
                    <ArrowDown className="size-3 inline-block" />
                    <span> Descending</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Content: loading / error / empty / table */}
      {renderContent()}
    </div>
  );
};
