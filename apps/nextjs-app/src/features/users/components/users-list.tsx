'use client';

import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { formatDate } from '@/utils/format';

import { useUsers } from '../api/get-users';

import { DeleteUser } from './delete-user';

export const UsersList = () => {
  const usersQuery = useUsers();

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
  );
};
