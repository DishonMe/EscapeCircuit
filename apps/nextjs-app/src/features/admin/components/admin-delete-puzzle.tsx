'use client';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useAdminDeletePuzzle } from '../api/delete-puzzle';

type AdminDeletePuzzleProps = {
  puzzleId: number;
  puzzleName: string;
};

export const AdminDeletePuzzle = ({
  puzzleId,
  puzzleName,
}: AdminDeletePuzzleProps) => {
  const { addNotification } = useNotifications();
  const mutation = useAdminDeletePuzzle({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: `Puzzle "${puzzleName}" deleted`,
        });
      },
    },
  });

  return (
    <ConfirmationDialog
      icon="danger"
      title="Delete Puzzle"
      body={`Permanently delete puzzle "${puzzleName}"? This will also delete all solve attempts, ratings, and test cases.`}
      triggerButton={
        <Button variant="destructive" size="sm">
          Delete
        </Button>
      }
      confirmButton={
        <Button
          isLoading={mutation.isPending}
          type="button"
          variant="destructive"
          onClick={() => mutation.mutate({ puzzleId })}
        >
          Delete Puzzle
        </Button>
      }
    />
  );
};
