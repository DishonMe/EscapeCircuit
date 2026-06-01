'use client';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';
import { isPendingCreator } from '@/lib/authorization';

import { useAcceptCreator, useDeclineCreator } from '../api/accept-creator';

export const CreatorInviteBanner = () => {
  const user = useUser();
  const { addNotification } = useNotifications();

  const accept = useAcceptCreator({
    mutationConfig: {
      onSuccess: () =>
        addNotification({
          type: 'success',
          title: 'You are now a Creator!',
        }),
    },
  });

  const decline = useDeclineCreator({
    mutationConfig: {
      onSuccess: () =>
        addNotification({
          type: 'info',
          title: 'Creator invitation declined.',
        }),
    },
  });

  if (!isPendingCreator(user.data)) return null;

  return (
    <div className="mb-4 flex flex-col items-start justify-between gap-3 rounded-xl border border-border bg-card p-4 shadow-card sm:flex-row sm:items-center">
      <div>
        <p className="text-[13px] font-medium text-foreground">
          You have been invited to become a Creator!
        </p>
        <p className="text-[13px] text-muted-foreground">
          Accept to start creating puzzles, or decline to remain a Solver.
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Button
          onClick={() => accept.mutate()}
          isLoading={accept.isPending}
          size="sm"
        >
          Accept
        </Button>
        <Button
          variant="outline"
          onClick={() => decline.mutate()}
          isLoading={decline.isPending}
          size="sm"
        >
          Decline
        </Button>
      </div>
    </div>
  );
};
