'use client';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useAdminUnpublishPuzzle } from '../api/admin-unpublish-puzzle';

type AdminUnpublishPuzzleProps = {
  puzzleId: number;
  puzzleName: string;
};

export const AdminUnpublishPuzzle = ({
  puzzleId,
  puzzleName,
}: AdminUnpublishPuzzleProps) => {
  const { addNotification } = useNotifications();
  const mutation = useAdminUnpublishPuzzle({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: `Puzzle "${puzzleName}" unpublished`,
        });
      },
    },
  });

  return (
    <ConfirmationDialog
      icon="info"
      title="Unpublish Puzzle"
      body={`Unpublish puzzle "${puzzleName}"? The creator will be notified. If the creator is over their unpublished limit they will be temporarily blocked from editing or creating puzzles until they remove enough.`}
      triggerButton={
        <Button variant="outline" size="sm">
          Unpublish
        </Button>
      }
      confirmButton={
        <Button
          isLoading={mutation.isPending}
          type="button"
          onClick={() => mutation.mutate({ puzzleId })}
        >
          Unpublish Puzzle
        </Button>
      }
    />
  );
};
