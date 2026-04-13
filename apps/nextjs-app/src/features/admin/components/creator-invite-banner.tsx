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
    <div className="rounded-xl border border-border bg-card p-4 shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
      <div>
        <p className="font-medium text-foreground text-[13px]">
          You have been invited to become a Creator!
        </p>
        <p className="text-[13px] text-muted-foreground">
          Accept to start creating puzzles, or decline to remain a Solver.
        </p>
      </div>
      <div className="flex gap-2 shrink-0">
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
