'use client';

import { Pin, Lock, ArrowLeft, Bell, BellOff, Bookmark } from 'lucide-react';
import NextLink from 'next/link';
import { useEffect, useRef } from 'react';

import { AvatarDisplay } from '@/components/ui/avatar-display';
import { Button } from '@/components/ui/button';
import { MDPreview } from '@/components/ui/md-preview';
import { useNotifications } from '@/components/ui/notifications';
import { Spinner } from '@/components/ui/spinner';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';
import {
  canPinDiscussion,
  canLockDiscussion,
  canDeleteDiscussion,
} from '@/lib/authorization';
import { cn } from '@/utils/cn';

import { useToggleBookmark } from '../api/bookmark-discussion';
import { useDeleteDiscussion } from '../api/delete-discussion';
import { useFollowDiscussion } from '../api/follow-discussion';
import { useDiscussion } from '../api/get-discussion';
import { useLockDiscussion } from '../api/lock-discussion';
import { usePinDiscussion } from '../api/pin-discussion';
import { useReactToDiscussion } from '../api/react-discussion';
import { useReportDiscussion } from '../api/report-discussion';
import { useViewDiscussion } from '../api/view-discussion';
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

  const bookmarkMutation = useToggleBookmark({
    discussionId,
  });

  const reportMutation = useReportDiscussion();

  const pinMutation = usePinDiscussion({
    discussionId,
  });

  const lockMutation = useLockDiscussion({
    discussionId,
  });

  // Track view once per visit (not on refetches from mutations)
  const viewMutation = useViewDiscussion({ discussionId });
  const viewedRef = useRef(false);
  useEffect(() => {
    if (!viewedRef.current && discussionQuery.data) {
      viewedRef.current = true;
      viewMutation.mutate({ discussionId });
    }
  }, [discussionQuery.data]); // eslint-disable-line react-hooks/exhaustive-deps

  if (discussionQuery.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (discussionQuery.isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50/50 p-4">
        <p className="text-[13px] text-red-700">
          Failed to load discussion. It may have been deleted or you may not
          have permission to view it.
        </p>
        <NextLink
          href={paths.app.discussions.getHref()}
          className="mt-2 inline-flex items-center gap-1 text-[13px] text-foreground underline underline-offset-4 hover:text-foreground/80"
        >
          <ArrowLeft className="size-4" />
          Back to Discussions
        </NextLink>
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
        className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to Discussions
      </NextLink>

      {/* Thread header */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {discussion.is_pinned && <Pin className="size-4 text-blue-500" />}
          {discussion.is_locked && (
            <Lock className="size-4 text-muted-foreground" />
          )}
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
                onVote={(value) => voteMutation.mutate({ discussionId, value })}
                isLoading={voteMutation.isPending}
                size="md"
              />
            </div>
          )}

          <div className="flex-1">
            <h1 className="mb-2 text-xl font-semibold text-foreground">
              {discussion.title}
            </h1>

            <div className="mb-4 flex items-center gap-2 text-[13px] text-muted-foreground">
              <div className="flex items-center gap-2">
                {discussion.author && (
                  <AvatarDisplay
                    avatarName={discussion.author.avatar_name}
                    avatarColor={discussion.author.avatar_color}
                    size="sm"
                  />
                )}
                <span className="font-medium text-foreground">
                  {discussion.author?.username || 'Unknown'}
                </span>
              </div>
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

            <div className="prose prose-sm max-w-none text-foreground">
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
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <Button
            variant="outline"
            size="sm"
            className={cn(
              isFollowing && 'bg-foreground/5 border-foreground/20',
            )}
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
            className={cn(isBookmarked && 'border-amber-200/60 bg-amber-50/50')}
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => pinMutation.mutate({ discussionId })}
              isLoading={pinMutation.isPending}
            >
              <Pin className="mr-1 size-3" />
              {discussion.is_pinned ? 'Unpin' : 'Pin'}
            </Button>
          )}
          {canLockDiscussion(user.data) && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => lockMutation.mutate({ discussionId })}
              isLoading={lockMutation.isPending}
            >
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
        <h2 className="text-lg font-semibold text-foreground">
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
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="mb-3 text-[13px] font-medium text-foreground">
            Post a Reply
          </h3>
          <ReplyComposer discussionId={discussionId} />
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-secondary p-4 text-center text-[13px] text-muted-foreground">
          <Lock className="mx-auto mb-2 size-5" />
          This discussion is locked. No new replies can be posted.
        </div>
      )}
    </div>
  );
};
