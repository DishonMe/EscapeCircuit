'use client';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useAssignCreator } from '../api/assign-creator';

type AssignCreatorButtonProps = {
  userId: number;
  username: string;
};

export const AssignCreatorButton = ({
  userId,
  username,
}: AssignCreatorButtonProps) => {
  const { addNotification } = useNotifications();
  const mutation = useAssignCreator({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: `Creator invitation sent to ${username}`,
        });
      },
    },
  });

  return (
    <ConfirmationDialog
      icon="info"
      title="Assign Creator Role"
      body={`Invite "${username}" to become a Creator? They will need to accept the invitation.`}
      triggerButton={
        <Button variant="outline" size="sm">
          Make Creator
        </Button>
      }
      confirmButton={
        <Button
          isLoading={mutation.isPending}
          type="button"
          onClick={() => mutation.mutate({ targetUserId: userId })}
        >
          Send Invitation
        </Button>
      }
    />
  );
};
