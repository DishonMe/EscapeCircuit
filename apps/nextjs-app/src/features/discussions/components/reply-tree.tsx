'use client';

import { Reply } from '@/types/api';

import { ReplyItem } from './reply-item';

type ReplyTreeProps = {
  replies: (Reply & { children?: Reply[] })[];
  discussionId: string;
  discussionAuthorId?: number;
};

export const ReplyTree = ({
  replies,
  discussionId,
  discussionAuthorId,
}: ReplyTreeProps) => {
  if (!replies || replies.length === 0) {
    return (
      <p className="py-4 text-center text-[13px] text-muted-foreground">
        No replies yet. Be the first to respond!
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {replies.map((reply) => (
        <ReplyItem
          key={reply.id}
          reply={reply}
          discussionId={discussionId}
          discussionAuthorId={discussionAuthorId}
          depth={0}
        />
      ))}
    </div>
  );
};
