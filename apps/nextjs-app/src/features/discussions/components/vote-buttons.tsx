'use client';

import { ChevronUp, ChevronDown } from 'lucide-react';

import { cn } from '@/utils/cn';

type VoteButtonsProps = {
  upvotes: number;
  downvotes: number;
  userVote: number | null;
  onVote: (value: number) => void;
  isLoading?: boolean;
  size?: 'sm' | 'md';
};

export const VoteButtons = ({
  upvotes,
  downvotes,
  userVote,
  onVote,
  isLoading,
  size = 'sm',
}: VoteButtonsProps) => {
  const score = upvotes - downvotes;
  const iconClass = size === 'md' ? 'size-5' : 'size-4';

  return (
    <div className="flex items-center gap-0.5">
      <button
        className={cn(
          'rounded p-0.5 transition-colors hover:bg-green-50',
          userVote === 1
            ? 'text-green-600'
            : 'text-gray-400 hover:text-green-500',
        )}
        onClick={() => onVote(1)}
        disabled={isLoading}
        title="Upvote"
      >
        <ChevronUp className={iconClass} />
      </button>
      <span
        className={cn(
          'min-w-[1.5rem] text-center text-xs font-semibold',
          score > 0 && 'text-green-600',
          score < 0 && 'text-red-500',
          score === 0 && 'text-gray-500',
        )}
      >
        {score}
      </span>
      <button
        className={cn(
          'rounded p-0.5 transition-colors hover:bg-red-50',
          userVote === -1
            ? 'text-red-500'
            : 'text-gray-400 hover:text-red-400',
        )}
        onClick={() => onVote(-1)}
        disabled={isLoading}
        title="Downvote"
      >
        <ChevronDown className={iconClass} />
      </button>
    </div>
  );
};
