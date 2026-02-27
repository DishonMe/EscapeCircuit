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
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search discussions..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm text-gray-700 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
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
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              filters.category === opt.value || (!filters.category && !opt.value)
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
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
          className="ml-auto rounded-md border border-gray-300 px-2 py-1 text-xs"
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
        <div className="py-12 text-center text-sm text-gray-400">
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
            className="rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </span>
          <button
            disabled={currentPage >= totalPages}
            onClick={() =>
              setFilters((prev) => ({ ...prev, offset: currentPage * limit }))
            }
            className="rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
