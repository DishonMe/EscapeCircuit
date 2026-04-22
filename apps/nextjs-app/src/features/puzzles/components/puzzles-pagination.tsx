'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PuzzlesPaginationProps {
  page: number;
  totalPages: number;
  total?: number;
  pageSize: number;
  filteredCountOnPage?: number;
  medalFilter: 'all' | 'unsolved' | 'bronze' | 'silver' | 'gold';
  onPageChange: (page: number) => void;
}

function buildPageList(
  page: number,
  totalPages: number,
): (number | 'ellipsis-left' | 'ellipsis-right')[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | 'ellipsis-left' | 'ellipsis-right')[] = [];
  const showLeft = page > 3;
  const showRight = page < totalPages - 2;

  // Always show page 1
  pages.push(1);

  if (showLeft) {
    pages.push('ellipsis-left');
  }

  // Show current-1, current, current+1 (clamped within range)
  const start = Math.max(2, page - 1);
  const end = Math.min(totalPages - 1, page + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (showRight) {
    pages.push('ellipsis-right');
  }

  // Always show last page
  pages.push(totalPages);

  return pages;
}

const BTN_CLASS =
  'inline-flex size-8 items-center justify-center rounded-lg border border-border bg-background text-[13px] transition-colors hover:bg-secondary aria-[current=page]:bg-secondary aria-[current=page]:ring-1 aria-[current=page]:ring-foreground/20 disabled:pointer-events-none disabled:opacity-50';

export const PuzzlesPagination = ({
  page,
  totalPages,
  total,
  pageSize,
  filteredCountOnPage,
  medalFilter,
  onPageChange,
}: PuzzlesPaginationProps) => {
  const showServerSummary = medalFilter === 'all' && total !== undefined;

  const summary = showServerSummary
    ? `Showing ${(page - 1) * pageSize + 1}\u2013${Math.min(page * pageSize, total!)} of ${total}`
    : `${filteredCountOnPage ?? 0} matches on this page`;

  const pageList = buildPageList(page, totalPages);

  return (
    <div className="mt-6 flex items-center justify-between gap-4 flex-wrap">
      {/* Result summary */}
      <span className="font-mono text-[12px] text-muted-foreground">
        {summary}
      </span>

      {/* Pagination buttons */}
      <div className="flex items-center gap-1">
        {/* Prev */}
        <button
          type="button"
          aria-label="Previous page"
          className={BTN_CLASS}
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="size-4" aria-hidden />
        </button>

        {/* Page buttons */}
        {pageList.map((item, idx) => {
          if (item === 'ellipsis-left' || item === 'ellipsis-right') {
            return (
              <span
                key={`${item}-${idx}`}
                className="inline-flex size-8 items-center justify-center text-[13px] text-muted-foreground select-none"
                aria-hidden
              >
                &hellip;
              </span>
            );
          }
          return (
            <button
              key={item}
              type="button"
              aria-label={`Page ${item}`}
              aria-current={item === page ? 'page' : undefined}
              className={BTN_CLASS}
              onClick={() => onPageChange(item)}
            >
              {item}
            </button>
          );
        })}

        {/* Next */}
        <button
          type="button"
          aria-label="Next page"
          className={BTN_CLASS}
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          <ChevronRight className="size-4" aria-hidden />
        </button>
      </div>
    </div>
  );
};
