'use client';

import { useState, ChangeEvent } from 'react';
import { Filter, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { formatDate } from '@/utils/format';

import { useUsers, UserFilters } from '../api/get-users';

import { DeleteUser } from './delete-user';

export const UsersList = () => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<UserFilters>({});

  const usersQuery = useUsers({ filters });

  const handleClearFilters = () => {
    setFilters({});
  };

  if (usersQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (usersQuery.isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Failed to load users. {usersQuery.error?.message && `Error: ${usersQuery.error.message}`}
        </p>
      </div>
    );
  }

  // The API returns { data: User[] } or just User[]
  const users = Array.isArray(usersQuery.data) 
    ? usersQuery.data 
    : usersQuery.data?.data;

  if (!users || users.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <p className="text-gray-600">No users found.</p>
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
          Filters {Object.values(filters).filter((v) => v).length > 0 && `(${Object.values(filters).filter((v) => v).length})`}
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
            {/* Username Search */}
            <div>
              <label className="text-sm font-medium text-gray-700">Username</label>
              <input
                type="text"
                placeholder="Search username..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.usernameSearch || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, usernameSearch: e.target.value || undefined })}
              />
            </div>

            {/* Role */}
            <div>
              <label className="text-sm font-medium text-gray-700">Role</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.role || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, role: (e.target.value || undefined) as any })}
              >
                <option value="">All Roles</option>
                <option value="solver">Solver</option>
                <option value="creator">Creator</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            {/* Experience Level */}
            <div>
              <label className="text-sm font-medium text-gray-700">Experience</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
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
              <label className="text-sm font-medium text-gray-700">Order By</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any })}
              >
                <option value="created_at">Creation Date</option>
                <option value="level">Level</option>
                <option value="role">Role</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-sm font-medium text-gray-700">Direction</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
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

      {/* Users Table */}
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
          },
          {
            title: 'Created At',
            field: 'createdAt',
            Cell({ entry: { createdAt } }) {
              return <span>{formatDate(createdAt)}</span>;
            },
          },
          {
            title: '',
            field: 'id',
            Cell({ entry: { id } }) {
              return <DeleteUser id={id} />;
            },
          },
        ]}
      />
    </div>
  );
};
