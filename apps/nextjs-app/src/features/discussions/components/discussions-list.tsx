'use client';

import { useState, useEffect, useMemo } from 'react';
import { Search } from 'lucide-react';

import { Spinner } from '@/components/ui/spinner';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';
import { ThreadCategory } from '@/types/api';
import { cn } from '@/utils/cn';

import { useDiscussions, DiscussionFilters } from '../api/get-discussions';
import { CATEGORY_OPTIONS } from './category-badge';
import { DiscussionCard } from './discussion-card';

const SORT_OPTIONS = [
  { value: 'newest' as const, label: 'Newest' },
  { value: 'oldest' as const, label: 'Oldest' },
  { value: 'most_replies' as const, label: 'Most Replies' },
  { value: 'most_upvotes' as const, label: 'Most Upvotes' },
  { value: 'trending' as const, label: 'Trending' },
];

export const DiscussionsList = () => {
  const [filters, setFilters] = useState<DiscussionFilters>({
    limit: 20,
    offset: 0,
    sort: 'newest',
  });
  const [searchInput, setSearchInput] = useState('');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({
        ...prev,
        search: searchInput || undefined,
        offset: 0,
      }));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const discussionsQuery = useDiscussions({ filters });

  const discussions = useMemo(() => {
    const rows = discussionsQuery.data?.discussions || [];
    return [...rows].sort(
      (a, b) =>
        Number(Boolean(b.is_bookmarked)) - Number(Boolean(a.is_bookmarked)),
    );
  }, [discussionsQuery.data?.discussions]);
  const total = discussionsQuery.data?.total ?? 0;
  const limit = filters.limit ?? 20;
  const offset = filters.offset ?? 0;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4">
      {/* Toolbar — search, chips, sort, bookmark toggle (single row, spread across) */}
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search discussions..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        <span aria-hidden className="hidden h-6 w-px shrink-0 bg-border/70 lg:block" />

        {/* Category chips */}
        <div
          role="group"
          aria-label="Filter by category"
          className="flex shrink-0 flex-nowrap items-center gap-1.5"
        >
          {CATEGORY_OPTIONS.map((opt) => (
            <button
              key={opt.value || 'all'}
              type="button"
              aria-pressed={
                filters.category === opt.value ||
                (!filters.category && !opt.value)
              }
              onClick={() =>
                setFilters((prev) => ({
                  ...prev,
                  category: opt.value
                    ? (opt.value as ThreadCategory)
                    : undefined,
                  offset: 0,
                }))
              }
              className={cn(
                'shrink-0 whitespace-nowrap rounded-full border border-border bg-background px-3 py-1 text-[12px] transition-colors hover:bg-secondary/40',
                'aria-pressed:bg-secondary aria-pressed:ring-1 aria-pressed:ring-foreground/20',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <span aria-hidden className="hidden h-6 w-px shrink-0 bg-border/70 lg:block" />

        {/* Sort */}
        <StyledSelect
          aria-label="Sort discussions"
          className="w-[150px] shrink-0"
          value={filters.sort ?? 'newest'}
          onValueChange={(v) =>
            setFilters((prev) => ({ ...prev, sort: v, offset: 0 }))
          }
          options={SORT_OPTIONS}
        />

        {/* Bookmarked toggle */}
        <label className="inline-flex shrink-0 cursor-pointer items-center gap-2 whitespace-nowrap rounded-lg border border-border bg-card px-3 py-2 text-[12px] text-foreground transition-colors hover:bg-secondary/40">
          <input
            type="checkbox"
            checked={filters.bookmarkedOnly ?? false}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                bookmarkedOnly: e.target.checked,
                offset: 0,
              }))
            }
            className="size-3.5 accent-primary"
          />
          Bookmarked only
        </label>
      </div>

      {discussionsQuery.isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : !discussions || discussions.length === 0 ? (
        <div className="py-12 text-center text-[13px] text-muted-foreground">
          {filters.bookmarkedOnly
            ? 'No bookmarked discussions yet.'
            : searchInput
              ? 'No discussions match your search.'
              : 'No discussions found. Start the conversation.'}
        </div>
      ) : (
        <div className="space-y-2">
          {discussions.map((d) => (
            <DiscussionCard key={d.id} discussion={d} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            disabled={currentPage <= 1}
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                offset: (currentPage - 2) * limit,
              }))
            }
            className="rounded-lg px-3 py-1 text-[13px] text-muted-foreground hover:bg-secondary disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-[13px] text-muted-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <button
            disabled={currentPage >= totalPages}
            onClick={() =>
              setFilters((prev) => ({ ...prev, offset: currentPage * limit }))
            }
            className="rounded-lg px-3 py-1 text-[13px] text-muted-foreground hover:bg-secondary disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
