'use client';

import { useState } from 'react';
import { CheckCircle, MessageSquare, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { MDPreview } from '@/components/ui/md-preview';
import { useNotifications } from '@/components/ui/notifications';
import { useUser } from '@/lib/auth';
import { Reply } from '@/types/api';
import { cn } from '@/utils/cn';

import { useAcceptReply } from '../api/accept-reply';
import { useDeleteReply } from '../api/delete-reply';
import { useReactToReply } from '../api/react-reply';
import { useReportReply } from '../api/report-reply';
import { useVoteReply } from '../api/vote-reply';
import { ReactionPicker } from './reaction-picker';
import { ReplyComposer } from './reply-composer';
import { ReportDialog } from './report-dialog';
import { UserBadge } from './user-badge';
import { VoteButtons } from './vote-buttons';

function timeAgo(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return new Date(ts).toLocaleDateString();
}

type ReplyItemProps = {
  reply: Reply & { children?: Reply[] };
  discussionId: string;
  discussionAuthorId?: number;
  depth?: number;
};

export const ReplyItem = ({
  reply,
  discussionId,
  discussionAuthorId,
  depth = 0,
}: ReplyItemProps) => {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const user = useUser();
  const { addNotification } = useNotifications();

  const acceptMutation = useAcceptReply({
    discussionId,
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: reply.is_accepted ? 'Solution unmarked' : 'Marked as solution',
        });
      },
    },
  });

  const deleteMutation = useDeleteReply({
    discussionId,
    mutationConfig: {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Reply deleted' });
      },
    },
  });

  const voteMutation = useVoteReply({
    discussionId,
  });

  const reactMutation = useReactToReply({
    discussionId,
  });

  const reportMutation = useReportReply();

  const canAccept =
    user.data &&
    (user.data.id === discussionAuthorId?.toString() ||
      user.data.role?.toLowerCase() === 'admin');

  const canDelete =
    user.data &&
    (user.data.id === reply.author_id?.toString() ||
      user.data.role?.toLowerCase() === 'admin');

  const maxNesting = 2;
  const engagement = reply.engagement;

  return (
    <div
      className={cn(
        'rounded-md border border-gray-100 bg-white p-3',
        reply.is_accepted && 'border-green-300 bg-green-50',
        depth > 0 && 'ml-6',
      )}
    >
      {reply.is_accepted && (
        <div className="mb-2 flex items-center gap-1 text-xs font-medium text-green-700">
          <CheckCircle className="size-3.5" />
          Accepted Solution
        </div>
      )}

      <div className="flex gap-3">
        {/* Vote buttons */}
        {engagement && (
          <div className="flex flex-col items-center pt-0.5">
            <VoteButtons
              upvotes={engagement.upvotes}
              downvotes={engagement.downvotes}
              userVote={engagement.user_vote}
              onVote={(value) =>
                voteMutation.mutate({ replyId: reply.id, value })
              }
              isLoading={voteMutation.isPending}
            />
          </div>
        )}

        <div className="flex-1">
          <div className="mb-2 flex items-center gap-2 text-xs text-gray-500">
            <span className="font-medium text-gray-700">
              {reply.author?.username || 'Unknown'}
            </span>
            <UserBadge user={reply.author} />
            <span>{timeAgo(reply.createdAt)}</span>
          </div>

          <div className="prose prose-sm max-w-none text-sm text-gray-700">
            <MDPreview value={reply.body} />
          </div>

          {/* Reactions */}
          {engagement && (
            <div className="mt-2">
              <ReactionPicker
                reactions={engagement.reactions}
                userReactions={engagement.user_reactions}
                onReact={(type) =>
                  reactMutation.mutate({
                    replyId: reply.id,
                    reactionType: type,
                  })
                }
                isLoading={reactMutation.isPending}
              />
            </div>
          )}

          <div className="mt-2 flex items-center gap-2">
            {depth < maxNesting && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-gray-500"
                onClick={() => setShowReplyForm(!showReplyForm)}
              >
                <MessageSquare className="mr-1 size-3" />
                Reply
              </Button>
            )}

            {canAccept && (
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  'h-7 text-xs',
                  reply.is_accepted ? 'text-green-600' : 'text-gray-500',
                )}
                onClick={() => acceptMutation.mutate({ replyId: reply.id })}
                isLoading={acceptMutation.isPending}
              >
                <CheckCircle className="mr-1 size-3" />
                {reply.is_accepted ? 'Unmark Solution' : 'Mark as Solution'}
              </Button>
            )}

            {canDelete && (
              <ConfirmationDialog
                icon="danger"
                title="Delete Reply"
                body="Are you sure you want to delete this reply?"
                triggerButton={
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-red-500"
                  >
                    <Trash2 className="mr-1 size-3" />
                    Delete
                  </Button>
                }
                confirmButton={
                  <Button
                    variant="destructive"
                    isLoading={deleteMutation.isPending}
                    onClick={() =>
                      deleteMutation.mutate({ replyId: reply.id })
                    }
                  >
                    Delete
                  </Button>
                }
              />
            )}

            <ReportDialog
              targetLabel="reply"
              onSubmit={({ reason, details }) =>
                reportMutation.mutate({
                  replyId: reply.id,
                  reason,
                  details,
                })
              }
              isLoading={reportMutation.isPending}
            />
          </div>
        </div>
      </div>

      {showReplyForm && (
        <div className="mt-3">
          <ReplyComposer
            discussionId={discussionId}
            parentReplyId={parseInt(reply.id)}
            onCancel={() => setShowReplyForm(false)}
            placeholder="Write a nested reply..."
          />
        </div>
      )}

      {reply.children && reply.children.length > 0 && (
        <div className="mt-3 space-y-2">
          {reply.children.map((child) => (
            <ReplyItem
              key={child.id}
              reply={child}
              discussionId={discussionId}
              discussionAuthorId={discussionAuthorId}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};
