'use client';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useRemoveCreator } from '../api/remove-creator';

type RemoveCreatorButtonProps = {
  userId: number;
  username: string;
  currentRole: string;
};

export const RemoveCreatorButton = ({
  userId,
  username,
  currentRole,
}: RemoveCreatorButtonProps) => {
  const { addNotification } = useNotifications();
  const mutation = useRemoveCreator({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: `Creator role removed from ${username}`,
        });
      },
    },
  });

  const bodyText =
    currentRole === 'creator'
      ? `Remove Creator role from "${username}"? Their draft puzzles will be permanently deleted. Published puzzles will remain.`
      : `Cancel the pending Creator invitation for "${username}"?`;

  return (
    <ConfirmationDialog
      icon="danger"
      title="Remove Creator Role"
      body={bodyText}
      triggerButton={
        <Button variant="destructive" size="sm">
          Remove Creator
        </Button>
      }
      confirmButton={
        <Button
          isLoading={mutation.isPending}
          type="button"
          variant="destructive"
          onClick={() => mutation.mutate({ targetUserId: userId })}
        >
          Remove Creator
        </Button>
      }
    />
  );
};
