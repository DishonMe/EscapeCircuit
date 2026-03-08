'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { User } from '@/types/api';
import { formatDate } from '@/utils/format';

import { useUsers } from '../api/get-users';

import { DeleteUser } from './delete-user';
import { PuzzleLimitsEditor } from './puzzle-limits-editor';

const MoreOptions = ({ user }: { user: User }) => {
  const [open, setOpen] = useState(false);
  // Only show for creators (and admins could have limits too, but mainly creators)
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
  const usersQuery = useUsers();

  if (usersQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const users = usersQuery.data?.data;

  if (!users) return null;

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
          title: 'Options',
          field: 'id',
          Cell({ entry }) {
            return (
              <div className="flex flex-col gap-1">
                <MoreOptions user={entry} />
              </div>
            );
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

