'use client';

import { useRouter } from 'next/navigation';
import { Loader, ChevronDown } from 'lucide-react';
import { useState, ChangeEvent } from 'react';

import { useUser } from '@/lib/auth';
import { useCreatorNotificationsHistory, NotificationFilters } from '@/features/notifications/api';

const NotificationsPage = () => {
  const user = useUser();
  const router = useRouter();
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<NotificationFilters>({
    orderBy: 'created_at',
    orderDirection: 'ASC',
  });

  const { data: notifications, isLoading, isError, error, refetch } = useCreatorNotificationsHistory({
    filters,
  });

  // Only allow creators and admins to view this page
  const userRole = user.data?.role?.toLowerCase() || '';
  if (user.status === 'success' && userRole !== 'creator' && userRole !== 'admin') {
    router.push('/app');
    return null;
  }

  return (
    <div className="max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Notifications</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          View and filter your creator notifications
        </p>
      </div>

      {/* Filters Toggle */}
      <div className="mb-6">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 rounded-lg bg-secondary/50 px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
        >
          Filters
          <ChevronDown
            className={`size-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
          />
        </button>

        {/* Filter Controls */}
        {showFilters && (
          <div className="mt-4 flex flex-wrap gap-4 rounded-lg border border-border bg-secondary/50 p-4">
            {/* Type Filter */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Type</label>
              <select
                className="w-full rounded border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
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
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Puzzle Name</label>
              <input
                type="text"
                placeholder="Search puzzle..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.puzzleName || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, puzzleName: e.target.value || undefined })}
              />
            </div>

            {/* Actor Username Filter */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Actor</label>
              <input
                type="text"
                placeholder="Search user..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.actorUsername || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, actorUsername: e.target.value || undefined })}
              />
            </div>

            {/* Order By */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Order By</label>
              <select
                className="w-full rounded border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: e.target.value as any })}
              >
                <option value="created_at">Creation Date</option>
                <option value="xp_amount">XP Amount</option>
              </select>
            </div>

            {/* Direction */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Direction</label>
              <select
                className="w-full rounded border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                value={filters.orderDirection || 'ASC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderDirection: e.target.value as any })}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
              </select>
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
            No notifications yet. Your creator notifications will appear here.
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
