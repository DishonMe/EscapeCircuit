'use client';

import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

import { Spinner } from '@/components/ui/spinner';
import { ThreadCategory } from '@/types/api';
import { cn } from '@/utils/cn';

import { useDiscussions, DiscussionFilters } from '../api/get-discussions';
import { CATEGORY_OPTIONS } from './category-badge';
import { DiscussionCard } from './discussion-card';

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

  const discussions = discussionsQuery.data?.discussions;
  const total = discussionsQuery.data?.total ?? 0;
  const limit = filters.limit ?? 20;
  const offset = filters.offset ?? 0;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search discussions..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="w-full rounded-lg border border-border bg-card py-2 pl-10 pr-4 text-[13px] text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {CATEGORY_OPTIONS.map((opt) => (
          <button
            key={opt.value || 'all'}
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                category: opt.value ? (opt.value as ThreadCategory) : undefined,
                offset: 0,
              }))
            }
            className={cn(
              'rounded-full px-3 py-1 text-[11px] font-medium transition-colors',
              filters.category === opt.value || (!filters.category && !opt.value)
                ? 'bg-foreground/5 border border-foreground/20 text-foreground'
                : 'bg-secondary text-muted-foreground hover:bg-secondary',
            )}
          >
            {opt.label}
          </button>
        ))}

        <select
          value={filters.sort ?? 'newest'}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              sort: e.target.value as DiscussionFilters['sort'],
              offset: 0,
            }))
          }
          className="ml-auto rounded-lg border border-border px-2 py-1 text-[11px]"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="most_replies">Most Replies</option>
          <option value="most_upvotes">Most Upvotes</option>
          <option value="trending">Trending</option>
        </select>
      </div>

      {discussionsQuery.isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : !discussions || discussions.length === 0 ? (
        <div className="py-12 text-center text-[13px] text-muted-foreground">
          {searchInput
            ? 'No discussions match your search.'
            : 'No discussions found. Start the conversation!'}
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
              setFilters((prev) => ({ ...prev, offset: (currentPage - 2) * limit }))
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
