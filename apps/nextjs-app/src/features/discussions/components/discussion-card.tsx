'use client';

import { MessageSquare, Eye, Pin, Lock, CheckCircle } from 'lucide-react';
import NextLink from 'next/link';

import { paths } from '@/config/paths';
import { Discussion } from '@/types/api';
import { cn } from '@/utils/cn';

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

  return (
    <NextLink
      href={paths.app.discussion.getHref(discussion.id)}
      className={cn(
        'block rounded-xl border border-border bg-card p-4 transition-all hover:border-foreground/20 hover:shadow-card',
        discussion.is_pinned && 'border-l-4 border-l-blue-500',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
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
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-[11px] text-muted-foreground">
        <span className="font-medium text-muted-foreground">
          {discussion.author?.username || 'Unknown'}
        </span>
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
      </div>
    </NextLink>
  );
};
