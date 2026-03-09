'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Filter, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { User } from '@/types/api';
import { formatDate } from '@/utils/format';

import { useUsers, UserFilters } from '../api/get-users';

import { DeleteUser } from './delete-user';
import { AssignCreatorButton } from '@/features/admin/components/assign-creator-button';
import { RemoveCreatorButton } from '@/features/admin/components/remove-creator-button';
import { PuzzleLimitsEditor } from './puzzle-limits-editor';

// Debounce hook — delays value updates until user stops typing
function useDebouncedValue<T>(value: T, delay: number = 400): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

const MoreOptions = ({ user }: { user: User }) => {
  const [open, setOpen] = useState(false);
  if (user.role !== 'creator') return null;
  return (
    <div>
      <Button
        size="sm"
        variant="outline"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? 'Hide Options' : 'More Options'}
      </Button>
      {open && <PuzzleLimitsEditor user={user} />}
    </div>
  );
};

export const UsersList = () => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<UserFilters>({});

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
          <p className="text-[13px] text-muted-foreground">No users found.</p>
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
                solver: 'bg-secondary text-muted-foreground',
                pending_creator: 'bg-amber-50/50 text-amber-700',
              };
              const color = roleColors[role] || 'bg-secondary text-muted-foreground';
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
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2 items-center">
                    {entry.role === 'solver' && (
                      <AssignCreatorButton
                        userId={Number(entry.id)}
                        username={entry.username}
                      />
                    )}
                    {(entry.role === 'creator' || entry.role === 'pending_creator') && (
                      <RemoveCreatorButton
                        userId={Number(entry.id)}
                        username={entry.username}
                        currentRole={entry.role}
                      />
                    )}
                    <DeleteUser id={entry.id} />
                  </div>
                  <MoreOptions user={entry} />
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
          Filters {Object.values(filters).filter((v) => v).length > 0 && `(${Object.values(filters).filter((v) => v).length})`}
        </Button>
        {Object.values(filters).filter((v) => v).length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="text-muted-foreground"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel — always visible when toggled */}
      {showFilters && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Username Search */}
            <div>
              <label className="text-[13px] font-medium text-foreground">Username</label>
              <input
                type="text"
                placeholder="Search username..."
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.usernameSearch || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, usernameSearch: e.target.value || undefined })}
              />
            </div>

            {/* Role */}
            <div>
              <label className="text-[13px] font-medium text-foreground">Role</label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.role || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, role: (e.target.value || undefined) as any })}
              >
                <option value="">All Roles</option>
                <option value="solver">Solver</option>
                <option value="creator">Creator</option>
                <option value="pending_creator">Pending Creator</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            {/* Experience Level */}
            <div>
              <label className="text-[13px] font-medium text-foreground">Experience</label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.experienceLevel || 'all'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, experienceLevel: e.target.value as any })}
              >
                <option value="all">All</option>
                <option value="experienced">Experienced (Lvl 5+)</option>
                <option value="inexperienced">Inexperienced (Lvl 1-4)</option>
              </select>
            </div>

            {/* Order By */}
            <div>
              <label className="text-[13px] font-medium text-foreground">Order By</label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any })}
              >
                <option value="created_at">Creation Date</option>
                <option value="level">Level</option>
                <option value="experienced">Experienced Status</option>
                <option value="role">Role</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-[13px] font-medium text-foreground">Direction</label>
              <select
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderDirection || 'ASC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderDirection: e.target.value as any })}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
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
