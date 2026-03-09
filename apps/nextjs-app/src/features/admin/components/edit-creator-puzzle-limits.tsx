'use client';

import { useState } from 'react';

import { Settings2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog/dialog';
import { useNotifications } from '@/components/ui/notifications';

import { useSetCreatorPuzzleLimits } from '../api/set-creator-puzzle-limits';

type EditCreatorPuzzleLimitsProps = {
  userId: number;
  username: string;
  currentMaxPublished: number;
  currentMaxUnpublished: number;
};

export const EditCreatorPuzzleLimits = ({
  userId,
  username,
  currentMaxPublished,
  currentMaxUnpublished,
}: EditCreatorPuzzleLimitsProps) => {
  const { addNotification } = useNotifications();
  const [open, setOpen] = useState(false);
  const [maxPublished, setMaxPublished] = useState(currentMaxPublished);
  const [maxUnpublished, setMaxUnpublished] = useState(currentMaxUnpublished);

  const mutation = useSetCreatorPuzzleLimits({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: `Puzzle limits updated for ${username}`,
        });
        setOpen(false);
      },
      onError: (error: any) => {
        addNotification({
          type: 'error',
          title: 'Failed to update puzzle limits',
          message:
            error?.response?.data?.detail || error?.message || 'Unknown error',
        });
      },
    },
  });

  const handleSave = () => {
    mutation.mutate({
      targetUserId: userId,
      maxPublished,
      maxUnpublished,
    });
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen) {
      setMaxPublished(currentMaxPublished);
      setMaxUnpublished(currentMaxUnpublished);
    }
    setOpen(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Settings2 className="size-3.5" />
          {'Puzzle Limits'}
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {'Edit Puzzle Limits — '}
            {username}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <p className="text-[13px] text-muted-foreground">
            Set the maximum number of published and unpublished puzzles this
            creator can have. If the current count exceeds the new limit,
            existing puzzles are kept but the creator cannot create or edit new
            puzzles until they are below the limit.
          </p>

          {/* Published limit */}
          <div className="space-y-1.5">
            <p className="text-[13px] font-medium text-foreground">
              Max Published Puzzles
            </p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Decrease published limit"
                onClick={() => setMaxPublished((v) => Math.max(0, v - 1))}
                className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary font-bold text-lg leading-none text-foreground transition-colors hover:bg-muted"
              >
                {'-'}
              </button>
              <span className="min-w-10 text-center text-[15px] font-semibold tabular-nums">
                {maxPublished}
              </span>
              <button
                type="button"
                aria-label="Increase published limit"
                onClick={() => setMaxPublished((v) => v + 1)}
                className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary font-bold text-lg leading-none text-foreground transition-colors hover:bg-muted"
              >
                {'+'}
              </button>
            </div>
          </div>

          {/* Unpublished limit */}
          <div className="space-y-1.5">
            <p className="text-[13px] font-medium text-foreground">
              Max Unpublished Puzzles
            </p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Decrease unpublished limit"
                onClick={() => setMaxUnpublished((v) => Math.max(0, v - 1))}
                className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary font-bold text-lg leading-none text-foreground transition-colors hover:bg-muted"
              >
                {'-'}
              </button>
              <span className="min-w-10 text-center text-[15px] font-semibold tabular-nums">
                {maxUnpublished}
              </span>
              <button
                type="button"
                aria-label="Increase unpublished limit"
                onClick={() => setMaxUnpublished((v) => v + 1)}
                className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary font-bold text-lg leading-none text-foreground transition-colors hover:bg-muted"
              >
                {'+'}
              </button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            isLoading={mutation.isPending}
            onClick={handleSave}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
