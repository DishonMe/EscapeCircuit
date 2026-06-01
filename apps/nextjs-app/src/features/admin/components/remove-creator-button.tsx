'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';
import { Spinner } from '@/components/ui/spinner';

import {
  useRemoveCreator,
  useConfirmRemoveCreator,
  RemoveCreatorResponse,
  ConfirmRemoveCreatorResponse,
} from '../api/remove-creator';

type RemoveCreatorButtonProps = {
  userId: number;
  username: string;
  currentRole: string;
};

type Step = 'initial' | 'action_selection' | 'closed';

export const RemoveCreatorButton = ({
  userId,
  username,
  currentRole,
}: RemoveCreatorButtonProps) => {
  const { addNotification } = useNotifications();
  const [step, setStep] = useState<Step>('closed');
  const [puzzlesData, setPuzzlesData] = useState<RemoveCreatorResponse | null>(
    null,
  );

  const initialMutation = useRemoveCreator({
    mutationConfig: {
      onSuccess: (data) => {
        if (data.was_pending) {
          addNotification({
            type: 'success',
            title: `Pending Creator invitation cancelled for ${username}`,
          });
          setStep('closed');
        } else if (data.admin_action_required) {
          // Move to step 2: choose action for published puzzles
          setPuzzlesData(data);
          setStep('action_selection');
        } else {
          addNotification({
            type: 'success',
            title: `Creator role removed from ${username}`,
          });
          setStep('closed');
        }
      },
      onError: (error: any) => {
        addNotification({
          type: 'error',
          title: 'Failed to remove Creator role',
          message: error?.message,
        });
        setStep('closed');
      },
    },
  });

  const confirmMutation = useConfirmRemoveCreator({
    mutationConfig: {
      onSuccess: (data: ConfirmRemoveCreatorResponse) => {
        const actionText =
          data.action === 'delete'
            ? 'deleted'
            : data.action === 'unpublish'
              ? 'unpublished'
              : 'left published';
        addNotification({
          type: 'success',
          title: `Creator role removed from ${username}`,
          message: `${data.published_affected} puzzle(s) ${actionText}`,
        });
        setStep('closed');
        setPuzzlesData(null);
      },
      onError: (error: any) => {
        addNotification({
          type: 'error',
          title: 'Failed to confirm Creator removal',
          message: error?.message,
        });
      },
    },
  });

  const handleInitialRemove = () => {
    initialMutation.mutate({ targetUserId: userId });
  };

  const handleConfirmAction = (action: 'unpublish' | 'delete' | 'leave') => {
    confirmMutation.mutate({ targetUserId: userId, action });
  };

  const handleCancel = () => {
    setStep('closed');
    setPuzzlesData(null);
  };

  const isPendingRemoval = currentRole === 'pending_creator';
  const bodyText = isPendingRemoval
    ? `Cancel the pending Creator invitation for "${username}"?`
    : `Remove Creator role from "${username}"? Their draft puzzles will be permanently deleted.`;

  return (
    <>
      {step === 'initial' && (
        <ConfirmationDialog
          icon="danger"
          title={
            isPendingRemoval
              ? 'Cancel Creator Invitation'
              : 'Remove Creator Role'
          }
          body={bodyText}
          triggerButton={
            <Button variant="destructive" size="sm">
              {isPendingRemoval ? 'Cancel Invitation' : 'Remove Creator'}
            </Button>
          }
          confirmButton={
            <Button
              isLoading={initialMutation.isPending}
              type="button"
              variant="destructive"
              onClick={handleInitialRemove}
            >
              {isPendingRemoval ? 'Cancel Invitation' : 'Remove Creator'}
            </Button>
          }
        />
      )}

      {step === 'closed' && (
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setStep('initial')}
        >
          {isPendingRemoval ? 'Cancel Invitation' : 'Remove Creator'}
        </Button>
      )}

      {/* Dialog for choosing action on published puzzles */}
      {step === 'action_selection' && puzzlesData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
            <h2 className="mb-4 text-lg font-semibold">
              Handle Published Puzzles
            </h2>

            <div className="mb-6 space-y-2">
              <p className="text-sm text-muted-foreground">
                {username} has {puzzlesData.published_count} published
                puzzle(s):
              </p>
              <ul className="max-h-32 space-y-1 overflow-y-auto text-sm">
                {puzzlesData.published_puzzles?.map((puzzle) => (
                  <li key={puzzle.id} className="text-muted-foreground">
                    • {puzzle.name}
                  </li>
                ))}
              </ul>
            </div>

            <p className="mb-4 text-sm font-medium">
              What would you like to do with these puzzles?
            </p>

            <div className="space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => handleConfirmAction('leave')}
                disabled={confirmMutation.isPending}
              >
                {confirmMutation.isPending ? (
                  <Spinner className="mr-2" />
                ) : null}
                Leave Published (No changes)
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => handleConfirmAction('unpublish')}
                disabled={confirmMutation.isPending}
              >
                {confirmMutation.isPending ? (
                  <Spinner className="mr-2" />
                ) : null}
                Unpublish All
              </Button>
              <Button
                variant="destructive"
                className="w-full justify-start"
                onClick={() => handleConfirmAction('delete')}
                disabled={confirmMutation.isPending}
              >
                {confirmMutation.isPending ? (
                  <Spinner className="mr-2" />
                ) : null}
                Delete All
              </Button>
            </div>

            <Button
              variant="ghost"
              className="mt-3 w-full"
              onClick={handleCancel}
              disabled={confirmMutation.isPending}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </>
  );
};
