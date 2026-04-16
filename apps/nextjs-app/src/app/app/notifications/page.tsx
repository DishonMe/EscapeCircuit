'use client';

import { useRouter } from 'next/navigation';
import { Loader, Filter, X, ArrowUp, ArrowDown } from 'lucide-react';
import { useState, useEffect, ChangeEvent } from 'react';

import { Button } from '@/components/ui/button';
import { useUser } from '@/lib/auth';
import { useCreatorNotificationsHistory, NotificationFilters } from '@/features/notifications/api';

const defaultFilters: Pick<NotificationFilters, 'orderBy' | 'orderDirection'> = {
  orderBy: 'created_at',
  orderDirection: 'ASC',
};

const NotificationsPage = () => {
  const user = useUser();
  const router = useRouter();
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<NotificationFilters>({
    ...defaultFilters,
  });
  const activeFilterCount = Object.entries(filters).reduce((count, [key, value]) => {
    if (value === undefined || value === null || value === '') return count;
    if (key === 'orderBy' && value === defaultFilters.orderBy) return count;
    if (key === 'orderDirection' && value === defaultFilters.orderDirection) return count;
    return count + 1;
  }, 0);

  const handleClearFilters = () => {
    setFilters({ ...defaultFilters });
  };

  const { data: notifications, isLoading, isError, error, refetch } = useCreatorNotificationsHistory({
    filters,
  });

  // Only allow creators and admins to view this page
  const userRole = user.data?.role?.toLowerCase() || '';
  const shouldRedirect = user.status === 'success' && userRole !== 'creator' && userRole !== 'admin';

  useEffect(() => {
    if (shouldRedirect) {
      router.push('/app');
    }
  }, [shouldRedirect, router]);

  if (shouldRedirect) return null;

  return (
    <div className="max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Notifications 🔔</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          View and filter your creator notifications
        </p>
      </div>

      {/* Filter Controls */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <Filter className="size-4" />
            Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
          </Button>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilters}
              className="text-muted-foreground text-[13px]"
            >
              <X className="size-4" />
              Clear
            </Button>
          )}
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="rounded-xl border border-border bg-card p-5 space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Type Filter */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Type</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.notifType || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, notifType: (e.target.value || undefined) as any })}
              >
                <option value="">All Types</option>
                <option value="solve">Puzzle Solved</option>
                <option value="rating">Rating</option>
                <option value="warning">Warning</option>
                <option value="ban">Account Restriction</option>
              </select>
            </div>

            {/* Puzzle Name Filter */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Puzzle Name</label>
              <input
                type="text"
                placeholder="Search puzzle..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.puzzleName || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, puzzleName: e.target.value || undefined })}
              />
            </div>

            {/* Actor Username Filter */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Actor</label>
              <input
                type="text"
                placeholder="Search user..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.actorUsername || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, actorUsername: e.target.value || undefined })}
              />
            </div>

            {/* Order By */}
            <div>
              <label className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Order By</label>
              <select
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any })}
              >
                <option value="created_at">Creation Date</option>
                <option value="xp_amount">XP Amount</option>
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Direction</label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const currentDirection = filters.orderDirection || 'ASC';
                  const newDirection = currentDirection === 'ASC' ? 'DESC' : 'ASC';
                  setFilters({ ...filters, orderDirection: newDirection as any });
                }}
                className="gap-1 px-2 py-1 inline-flex items-center whitespace-nowrap"
              >
                {(filters.orderDirection || 'ASC') === 'ASC' ? (
                  <>
                    <ArrowUp className="size-3 inline-block" />
                    <span> Ascending</span>
                  </>
                ) : (
                  <>
                    <ArrowDown className="size-3 inline-block" />
                    <span> Descending</span>
                  </>
                )}
              </Button>
            </div>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader className="size-6 animate-spin text-foreground/40" />
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-red-200/60 bg-red-50/50 p-4">
          <p className="text-[13px] text-red-700">
            Failed to load notifications. {error?.message && `Error: ${error.message}`}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 rounded-lg bg-red-600 px-3 py-1 text-[11px] text-white hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : !notifications || notifications.length === 0 ? (
        <div className="rounded-xl border border-border bg-secondary/50 p-8 text-center">
          <p className="text-[13px] text-muted-foreground">
            No notifications yet. 🔔 Your creator notifications will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className="rounded-xl border border-border bg-card p-4 transition-colors hover:bg-secondary/50"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex rounded-md px-3 py-1 text-[11px] font-medium ${
                        notification.type === 'solve'
                          ? 'bg-emerald-50/50 text-emerald-700'
                          : notification.type === 'warning'
                          ? 'bg-amber-50/50 text-amber-700'
                          : notification.type === 'ban'
                          ? 'bg-red-50/50 text-red-700'
                          : 'bg-blue-50/50 text-blue-700'
                      }`}
                    >
                      {notification.type === 'solve' ? 'Puzzle Solved' : notification.type === 'warning' ? 'Warning' : notification.type === 'ban' ? 'Account Restriction' : 'Rating'}
                    </span>
                    <span className="text-[13px] font-medium text-foreground">
                      {notification.puzzle_name}
                    </span>
                  </div>
                  <p className="mt-2 text-[13px] text-muted-foreground">
                    {notification.message}
                  </p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    By {notification.actor_username}
                    {notification.xp_amount > 0 && (
                      <span className="ml-2 font-medium text-green-600">
                        +{notification.xp_amount} XP
                      </span>
                    )}
                  </p>
                </div>
                <div className="ml-4 text-right">
                  <p className="text-[11px] text-muted-foreground">
                    {new Date(notification.created_at).toLocaleDateString()}
                  </p>
                  <p className="text-[11px] text-muted-foreground/70">
                    {new Date(notification.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default NotificationsPage;
