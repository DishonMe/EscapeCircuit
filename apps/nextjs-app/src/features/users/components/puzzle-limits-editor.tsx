'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { User } from '@/types/api';

import { useUpdatePuzzleLimits } from '../api/update-puzzle-limits';

type PuzzleLimitsEditorProps = {
  user: User;
};

export const PuzzleLimitsEditor = ({ user }: PuzzleLimitsEditorProps) => {
  const { addNotification } = useNotifications();

  const [maxPublished, setMaxPublished] = useState<number>(
    user.effective_published_limit ?? 5,
  );
  const [maxUnpublished, setMaxUnpublished] = useState<number>(
    user.effective_unpublished_limit ?? 5,
  );

  const updateMutation = useUpdatePuzzleLimits({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'Puzzle limits updated',
        });
      },
      onError: () => {
        addNotification({
          type: 'error',
          title: 'Failed to update puzzle limits',
        });
      },
    },
  });

  const handleSave = () => {
    updateMutation.mutate({
      userId: user.id,
      maxPublished,
      maxUnpublished,
    });
  };

  return (
    <div className="mt-2 rounded border border-gray-200 bg-gray-50 p-3 text-sm dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-2 font-semibold text-gray-700 dark:text-gray-300">
        Puzzle capacity overrides
      </p>

      {/* Published limit row */}
      <div className="mb-2 flex items-center gap-2">
        <span className="w-32 text-gray-600 dark:text-gray-400">Published</span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMaxPublished((v) => Math.max(0, v - 1))}
          aria-label="Decrease published limit"
        >
          −
        </Button>
        <span className="w-8 text-center font-mono">{maxPublished}</span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMaxPublished((v) => v + 1)}
          aria-label="Increase published limit"
        >
          +
        </Button>
      </div>

      {/* Unpublished limit row */}
      <div className="mb-3 flex items-center gap-2">
        <span className="w-32 text-gray-600 dark:text-gray-400">Unpublished</span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMaxUnpublished((v) => Math.max(0, v - 1))}
          aria-label="Decrease unpublished limit"
        >
          −
        </Button>
        <span className="w-8 text-center font-mono">{maxUnpublished}</span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMaxUnpublished((v) => v + 1)}
          aria-label="Increase unpublished limit"
        >
          +
        </Button>
      </div>

      <Button
        size="sm"
        isLoading={updateMutation.isPending}
        onClick={handleSave}
      >
        Save
      </Button>
    </div>
  );
};
