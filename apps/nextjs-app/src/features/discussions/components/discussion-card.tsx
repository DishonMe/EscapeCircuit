'use client';

import { MessageSquare, Eye, Pin, Lock, CheckCircle, Bookmark } from 'lucide-react';
import NextLink from 'next/link';

import { paths } from '@/config/paths';
import { Discussion } from '@/types/api';
import { cn } from '@/utils/cn';
import { AvatarDisplay } from '@/components/ui/avatar-display';

import { useToggleBookmark } from '../api/bookmark-discussion';
import { CategoryBadge } from './category-badge';
import { UserBadge } from './user-badge';

function timeAgo(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(ts).toLocaleDateString();
}

export const DiscussionCard = ({ discussion }: { discussion: Discussion }) => {
  const hasAcceptedSolution = discussion.accepted_reply_id != null;
  const isBookmarked = discussion.is_bookmarked ?? false;
  const bookmarkMutation = useToggleBookmark({
    discussionId: String(discussion.id),
  });

  return (
    <div
      className={cn(
        'block rounded-xl border border-border bg-card p-4 transition-all hover:border-foreground/20 hover:shadow-card',
        discussion.is_pinned && 'border-l-4 border-l-blue-500',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <NextLink
          href={paths.app.discussion.getHref(discussion.id)}
          className="min-w-0 flex-1"
        >
          <div className="mb-1 flex flex-wrap items-center gap-2">
            {discussion.is_pinned && (
              <Pin className="size-3.5 text-blue-500" />
            )}
            {discussion.is_locked && (
              <Lock className="size-3.5 text-muted-foreground" />
            )}
            <h3 className="truncate text-[13px] font-semibold text-foreground">
              {discussion.title}
            </h3>
          </div>

          <div className="mb-2 flex flex-wrap items-center gap-2">
            <CategoryBadge category={discussion.category} />
            {hasAcceptedSolution && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50/50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                <CheckCircle className="size-3" />
                Solved
              </span>
            )}
          </div>

          <p className="line-clamp-1 text-[11px] text-muted-foreground">
            {discussion.body.slice(0, 120)}
          </p>
        </NextLink>

        <button
          type="button"
          aria-label={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
          className={cn(
            'rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground',
            isBookmarked && 'text-yellow-600',
          )}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            bookmarkMutation.mutate({ discussionId: String(discussion.id) });
          }}
          disabled={bookmarkMutation.isPending}
        >
          <Bookmark
            className={cn('size-4', isBookmarked && 'fill-yellow-500 text-yellow-500')}
          />
        </button>
      </div>

      <NextLink
        href={paths.app.discussion.getHref(discussion.id)}
        className="mt-3 flex items-center gap-4 text-[11px] text-muted-foreground"
      >
        <div className="flex items-center gap-2">
          {discussion.author && (
            <AvatarDisplay
              avatarName={discussion.author.avatar_name}
              avatarColor={discussion.author.avatar_color}
              size="sm"
            />
          )}
          <span className="font-medium text-muted-foreground">
            {discussion.author?.username || 'Unknown'}
          </span>
        </div>
        <UserBadge user={discussion.author} />
        <span className="flex items-center gap-1">
          <MessageSquare className="size-3" />
          {discussion.reply_count}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="size-3" />
          {discussion.view_count}
        </span>
        <span className="ml-auto">{timeAgo(discussion.createdAt)}</span>
      </NextLink>
    </div>
  );
};
