'use client';

import { useState } from 'react';
import { Settings } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';

import { useUpdatePuzzleLimits } from '../api/update-puzzle-limits';

type CreatorPuzzleLimitsProps = {
  userId: number;
  username: string;
  /** Current effective max published (admin override or level-based default). */
  effectiveMaxPublished: number;
  /** Current effective max unpublished (admin override or level-based default). */
  effectiveMaxUnpublished: number;
  /** Admin-set override (null = using level default). */
  maxPublishedOverride: number | null;
  maxUnpublishedOverride: number | null;
};

export const CreatorPuzzleLimits = ({
  userId,
  username,
  effectiveMaxPublished,
  effectiveMaxUnpublished,
  maxPublishedOverride,
  maxUnpublishedOverride,
}: CreatorPuzzleLimitsProps) => {
  const [open, setOpen] = useState(false);
  const [maxPublished, setMaxPublished] = useState(effectiveMaxPublished);
  const [maxUnpublished, setMaxUnpublished] = useState(effectiveMaxUnpublished);
  const { addNotification } = useNotifications();

  const mutation = useUpdatePuzzleLimits({
    mutationConfig: {
      onSuccess: (data) => {
        addNotification({
          type: 'success',
          title: `Puzzle limits for ${username} updated`,
        });
        setOpen(false);
      },
      onError: (error: any) => {
        addNotification({
          type: 'error',
          title: 'Failed to update puzzle limits',
        });
      },
    },
  });

  const handleSave = () => {
    mutation.mutate({
      userId,
      maxPublished,
      maxUnpublished,
    });
  };

  const handleReset = () => {
    setMaxPublished(effectiveMaxPublished);
    setMaxUnpublished(effectiveMaxUnpublished);
  };

  if (!open) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-1"
        title="Edit puzzle limits"
      >
        <Settings className="size-3.5" />
        Limits
      </Button>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4 min-w-[260px]">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-foreground">
          Puzzle Limits for {username}
        </span>
        <button
          onClick={() => { handleReset(); setOpen(false); }}
          className="text-[11px] text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
      </div>

      {/* Published limit row */}
      <div className="space-y-1">
        <label className="text-[12px] font-medium text-foreground">
          Max Published
          {maxPublishedOverride === null && (
            <span className="ml-1 text-[11px] text-muted-foreground">(level default)</span>
          )}
        </label>
        <div className="flex items-center gap-2">
          <button
            className="rounded-md border border-border px-2 py-1 text-[13px] hover:bg-secondary disabled:opacity-50"
            onClick={() => setMaxPublished((v) => Math.max(0, v - 1))}
            disabled={maxPublished <= 0}
          >
            −
          </button>
          <span className="min-w-[32px] text-center text-[14px] font-medium">
            {maxPublished}
          </span>
          <button
            className="rounded-md border border-border px-2 py-1 text-[13px] hover:bg-secondary"
            onClick={() => setMaxPublished((v) => v + 1)}
          >
            +
          </button>
        </div>
      </div>

      {/* Unpublished limit row */}
      <div className="space-y-1">
        <label className="text-[12px] font-medium text-foreground">
          Max Unpublished
          {maxUnpublishedOverride === null && (
            <span className="ml-1 text-[11px] text-muted-foreground">(level default)</span>
          )}
        </label>
        <div className="flex items-center gap-2">
          <button
            className="rounded-md border border-border px-2 py-1 text-[13px] hover:bg-secondary disabled:opacity-50"
            onClick={() => setMaxUnpublished((v) => Math.max(0, v - 1))}
            disabled={maxUnpublished <= 0}
          >
            −
          </button>
          <span className="min-w-[32px] text-center text-[14px] font-medium">
            {maxUnpublished}
          </span>
          <button
            className="rounded-md border border-border px-2 py-1 text-[13px] hover:bg-secondary"
            onClick={() => setMaxUnpublished((v) => v + 1)}
          >
            +
          </button>
        </div>
      </div>

      <Button
        size="sm"
        className="w-full"
        isLoading={mutation.isPending}
        onClick={handleSave}
      >
        Save
      </Button>
    </div>
  );
};
