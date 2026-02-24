'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { useCreateReply } from '../api/create-reply';

type ReplyComposerProps = {
  discussionId: string;
  parentReplyId?: number | null;
  onCancel?: () => void;
  placeholder?: string;
};

export const ReplyComposer = ({
  discussionId,
  parentReplyId = null,
  onCancel,
  placeholder = 'Write a reply...',
}: ReplyComposerProps) => {
  const [body, setBody] = useState('');
  const { addNotification } = useNotifications();

  const createReplyMutation = useCreateReply({
    discussionId,
    mutationConfig: {
      onSuccess: () => {
        setBody('');
        addNotification({ type: 'success', title: 'Reply posted' });
        onCancel?.();
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    createReplyMutation.mutate({
      data: { body: body.trim(), parent_reply_id: parentReplyId },
      discussionId,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <div className="flex items-center gap-2">
        <Button
          type="submit"
          size="sm"
          isLoading={createReplyMutation.isPending}
          disabled={!body.trim()}
        >
          Post Reply
        </Button>
        {onCancel && (
          <Button type="button" size="sm" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
};
