'use client';

import { useState } from 'react';
import { Minus, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { User } from '@/types/api';
import { useUpdatePuzzleLimits } from '../api/update-puzzle-limits';

interface PuzzleLimitsEditorProps {
  user: User;
}

export const PuzzleLimitsEditor = ({ user }: PuzzleLimitsEditorProps) => {
  const effectivePublished = user.effective_published_limit ?? 5;
  const effectiveUnpublished = user.effective_unpublished_limit ?? 5;

  const [publishedLimit, setPublishedLimit] = useState<number>(
    user.puzzle_limit_published ?? effectivePublished,
  );
  const [unpublishedLimit, setUnpublishedLimit] = useState<number>(
    user.puzzle_limit_unpublished ?? effectiveUnpublished,
  );

  const mutation = useUpdatePuzzleLimits();

  const handleSave = () => {
    mutation.mutate({
      userId: Number(user.id),
      puzzle_limit_published: publishedLimit,
      puzzle_limit_unpublished: unpublishedLimit,
    });
  };

  const handleReset = () => {
    mutation.mutate({
      userId: Number(user.id),
      puzzle_limit_published: null,
      puzzle_limit_unpublished: null,
    });
    setPublishedLimit(effectivePublished);
    setUnpublishedLimit(effectiveUnpublished);
  };

  return (
    <div className="mt-2 rounded-lg border border-border bg-card p-3 space-y-3">
      <p className="text-[12px] font-semibold text-foreground">Puzzle Limits</p>

      {/* Published limit */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] text-muted-foreground">Published cap</span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setPublishedLimit((v) => Math.max(0, v - 1))}
            disabled={mutation.isPending}
          >
            <Minus className="size-3" />
          </Button>
          <span className="w-6 text-center text-[13px] font-medium">{publishedLimit}</span>
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setPublishedLimit((v) => v + 1)}
            disabled={mutation.isPending}
          >
            <Plus className="size-3" />
          </Button>
        </div>
      </div>

      {/* Unpublished limit */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] text-muted-foreground">Draft cap</span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setUnpublishedLimit((v) => Math.max(0, v - 1))}
            disabled={mutation.isPending}
          >
            <Minus className="size-3" />
          </Button>
          <span className="w-6 text-center text-[13px] font-medium">{unpublishedLimit}</span>
          <Button
            variant="outline"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setUnpublishedLimit((v) => v + 1)}
            disabled={mutation.isPending}
          >
            <Plus className="size-3" />
          </Button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          size="sm"
          className="flex-1 h-7 text-[12px]"
          onClick={handleSave}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? <Spinner size="sm" /> : 'Save'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-[12px]"
          onClick={handleReset}
          disabled={mutation.isPending}
          title="Reset to XP-based defaults"
        >
          Reset
        </Button>
      </div>

      {mutation.isError && (
        <p className="text-[11px] text-red-600">
          {(mutation.error as Error)?.message ?? 'Failed to update limits'}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="text-[11px] text-emerald-600">Limits updated.</p>
      )}
    </div>
  );
};
