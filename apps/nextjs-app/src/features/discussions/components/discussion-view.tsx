'use client';

import { Pin, Lock, ArrowLeft, Bell, BellOff, Bookmark } from 'lucide-react';
import NextLink from 'next/link';

import { Button } from '@/components/ui/button';
import { MDPreview } from '@/components/ui/md-preview';
import { Spinner } from '@/components/ui/spinner';
import { useNotifications } from '@/components/ui/notifications';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';
import {
  canPinDiscussion,
  canLockDiscussion,
  canDeleteDiscussion,
} from '@/lib/authorization';
import { cn } from '@/utils/cn';

import { useBookmarkDiscussion } from '../api/bookmark-discussion';
import { useDeleteDiscussion } from '../api/delete-discussion';
import { useFollowDiscussion } from '../api/follow-discussion';
import { useDiscussion } from '../api/get-discussion';
import { useReactToDiscussion } from '../api/react-discussion';
import { useReportDiscussion } from '../api/report-discussion';
import { useVoteDiscussion } from '../api/vote-discussion';
import { CategoryBadge } from './category-badge';
import { ReactionPicker } from './reaction-picker';
import { ReplyComposer } from './reply-composer';
import { ReplyTree } from './reply-tree';
import { ReportDialog } from './report-dialog';
import { UserBadge } from './user-badge';
import { VoteButtons } from './vote-buttons';

export const DiscussionView = ({ discussionId }: { discussionId: string }) => {
  const discussionQuery = useDiscussion({ discussionId });
  const user = useUser();
  const { addNotification } = useNotifications();

  const deleteMutation = useDeleteDiscussion({
    mutationConfig: {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Discussion deleted' });
        window.location.href = paths.app.discussions.getHref();
      },
    },
  });

  const voteMutation = useVoteDiscussion({
    discussionId,
  });

  const reactMutation = useReactToDiscussion({
    discussionId,
  });

  const followMutation = useFollowDiscussion({
    discussionId,
  });

  const bookmarkMutation = useBookmarkDiscussion({
    discussionId,
  });

  const reportMutation = useReportDiscussion();

  if (discussionQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const discussion = discussionQuery.data;
  if (!discussion) return null;

  const engagement = discussion.engagement;
  const isFollowing = engagement?.is_following ?? false;
  const isBookmarked = engagement?.is_bookmarked ?? false;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <NextLink
        href={paths.app.discussions.getHref()}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="size-4" />
        Back to Discussions
      </NextLink>

      {/* Thread header */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {discussion.is_pinned && <Pin className="size-4 text-blue-500" />}
          {discussion.is_locked && <Lock className="size-4 text-gray-400" />}
          <CategoryBadge category={discussion.category} />
        </div>

        <div className="flex gap-4">
          {/* Vote buttons */}
          {engagement && (
            <div className="flex flex-col items-center pt-1">
              <VoteButtons
                upvotes={engagement.upvotes}
                downvotes={engagement.downvotes}
                userVote={engagement.user_vote}
                onVote={(value) =>
                  voteMutation.mutate({ discussionId, value })
                }
                isLoading={voteMutation.isPending}
                size="md"
              />
            </div>
          )}

          <div className="flex-1">
            <h1 className="mb-2 text-xl font-bold text-gray-900">
              {discussion.title}
            </h1>

            <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700">
                {discussion.author?.username || 'Unknown'}
              </span>
              <UserBadge user={discussion.author} />
              <span>
                {new Date(discussion.createdAt).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </span>
              <span>{discussion.view_count} views</span>
              <span>{discussion.reply_count} replies</span>
            </div>

            <div className="prose prose-sm max-w-none text-gray-700">
              <MDPreview value={discussion.body} />
            </div>

            {/* Reactions */}
            {engagement && (
              <div className="mt-3">
                <ReactionPicker
                  reactions={engagement.reactions}
                  userReactions={engagement.user_reactions}
                  onReact={(type) =>
                    reactMutation.mutate({
                      discussionId,
                      reactionType: type,
                    })
                  }
                  isLoading={reactMutation.isPending}
                />
              </div>
            )}
          </div>
        </div>

        {/* Action bar: follow, bookmark, admin actions */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-4">
          <Button
            variant="outline"
            size="sm"
            className={cn(isFollowing && 'border-blue-300 bg-blue-50')}
            onClick={() => followMutation.mutate({ discussionId })}
            isLoading={followMutation.isPending}
          >
            {isFollowing ? (
              <BellOff className="mr-1 size-3" />
            ) : (
              <Bell className="mr-1 size-3" />
            )}
            {isFollowing ? 'Unfollow' : 'Follow'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            className={cn(isBookmarked && 'border-yellow-300 bg-yellow-50')}
            onClick={() => bookmarkMutation.mutate({ discussionId })}
            isLoading={bookmarkMutation.isPending}
          >
            <Bookmark
              className={cn(
                'mr-1 size-3',
                isBookmarked && 'fill-yellow-500 text-yellow-500',
              )}
            />
            {isBookmarked ? 'Bookmarked' : 'Bookmark'}
          </Button>

          <ReportDialog
            targetLabel="discussion"
            onSubmit={({ reason, details }) =>
              reportMutation.mutate({
                discussionId,
                reason,
                details,
              })
            }
            isLoading={reportMutation.isPending}
          />

          <div className="flex-1" />

          {canPinDiscussion(user.data) && (
            <Button variant="outline" size="sm">
              <Pin className="mr-1 size-3" />
              {discussion.is_pinned ? 'Unpin' : 'Pin'}
            </Button>
          )}
          {canLockDiscussion(user.data) && (
            <Button variant="outline" size="sm">
              <Lock className="mr-1 size-3" />
              {discussion.is_locked ? 'Unlock' : 'Lock'}
            </Button>
          )}
          {canDeleteDiscussion(user.data, discussion) && (
            <Button
              variant="destructive"
              size="sm"
              isLoading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate({ discussionId })}
            >
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Replies */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Replies ({discussion.reply_count})
        </h2>
        <ReplyTree
          replies={discussion.replies || []}
          discussionId={discussionId}
          discussionAuthorId={discussion.author_id}
        />
      </div>

      {/* Reply composer */}
      {!discussion.is_locked ? (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-medium text-gray-700">
            Post a Reply
          </h3>
          <ReplyComposer discussionId={discussionId} />
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-500">
          <Lock className="mx-auto mb-2 size-5" />
          This discussion is locked. No new replies can be posted.
        </div>
      )}
    </div>
  );
};
