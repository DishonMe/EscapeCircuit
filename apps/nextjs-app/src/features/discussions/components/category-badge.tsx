'use client';

import { cn } from '@/utils/cn';
import { ThreadCategory } from '@/types/api';

const categoryConfig: Record<
  ThreadCategory,
  { label: string; color: string }
> = {
  general: { label: 'General', color: 'bg-gray-100 text-gray-700' },
  puzzle_help: { label: 'Puzzle Help', color: 'bg-blue-100 text-blue-700' },
  puzzle_tips: { label: 'Tips & Tricks', color: 'bg-green-100 text-green-700' },
  solutions: { label: 'Solutions', color: 'bg-purple-100 text-purple-700' },
  bug_report: { label: 'Bug Report', color: 'bg-red-100 text-red-700' },
  feature_request: { label: 'Feature Request', color: 'bg-yellow-100 text-yellow-700' },
  showcase: { label: 'Showcase', color: 'bg-indigo-100 text-indigo-700' },
};

export const CategoryBadge = ({
  category,
  className,
}: {
  category: ThreadCategory;
  className?: string;
}) => {
  const config = categoryConfig[category] || categoryConfig.general;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        config.color,
        className,
      )}
    >
      {config.label}
    </span>
  );
};

export const CATEGORY_OPTIONS: { label: string; value: ThreadCategory }[] = [
  { label: 'All Categories', value: '' as ThreadCategory },
  { label: 'General', value: 'general' },
  { label: 'Puzzle Help', value: 'puzzle_help' },
  { label: 'Tips & Tricks', value: 'puzzle_tips' },
  { label: 'Solutions', value: 'solutions' },
  { label: 'Bug Report', value: 'bug_report' },
  { label: 'Feature Request', value: 'feature_request' },
  { label: 'Showcase', value: 'showcase' },
];
