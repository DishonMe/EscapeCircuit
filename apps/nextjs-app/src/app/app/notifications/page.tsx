'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Loader, Filter, X } from 'lucide-react';
import { ChangeEvent, useState } from 'react';

import { Button } from '@/components/ui/button';
import { useUser } from '@/lib/auth';
import { useCreatorNotificationsHistory, NotificationFilters } from '@/features/notifications/api';

const NotificationsPage = () => {
  const user = useUser();
  const router = useRouter();
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<NotificationFilters>({});

  const { data: notifications, isLoading, isError, error, refetch } = useCreatorNotificationsHistory({ filters });

  // Only allow creators and admins to view this page
  const userRole = user.data?.role?.toLowerCase() || '';
  if (user.status === 'success' && userRole !== 'creator' && userRole !== 'admin') {
    router.push('/app');
    return null;
  }

  const handleClearFilters = () => {
    setFilters({});
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        <p className="mt-2 text-gray-600">
          View all your creator notifications in one place
        </p>
      </div>

      {/* Filter Controls */}
      <div className="mb-4 flex items-center justify-between gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className="gap-2"
        >
          <Filter className="size-4" />
          Filters {Object.values(filters).filter((v) => v).length > 0 && `(${Object.values(filters).filter((v) => v).length})`}
        </Button>
        {Object.values(filters).filter((v) => v).length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="text-gray-600"
          >
            <X className="size-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex flex-wrap gap-4">
            {/* Notification Type */}
            <div className="flex-1 min-w-[120px]">
              <label className="text-sm font-medium text-gray-700">Type</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.notifType || ''}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, notifType: (e.target.value || undefined) as 'solve' | 'rating' | 'warning' | 'ban' | undefined })}
              >
                <option value="">All Types</option>
                <option value="solve">Puzzle Solved</option>
                <option value="rating">Rating</option>
                <option value="warning">Warning</option>
                <option value="ban">Ban</option>
              </select>
            </div>

            {/* Puzzle Name */}
            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium text-gray-700">Puzzle Name</label>
              <input
                type="text"
                placeholder="Search puzzle..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.puzzleName || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, puzzleName: e.target.value || undefined })}
              />
            </div>

            {/* Actor Username */}
            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium text-gray-700">Actor Username</label>
              <input
                type="text"
                placeholder="Search actor..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.actorUsername || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFilters({ ...filters, actorUsername: e.target.value || undefined })}
              />
            </div>

            {/* Order By */}
            <div className="flex-1 min-w-[120px]">
              <label className="text-sm font-medium text-gray-700">Order By</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderBy || 'created_at'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderBy: (e.target.value as any) })}
              >
                <option value="created_at">Date (Newest)</option>
                <option value="xp_amount">XP Amount</option>
              </select>
            </div>

            {/* Direction */}
            <div className="flex-1 min-w-[120px]">
              <label className="text-sm font-medium text-gray-700">Direction</label>
              <select
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                value={filters.orderDirection || 'ASC'}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilters({ ...filters, orderDirection: (e.target.value as any) })}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader className="size-6 animate-spin text-blue-600" />
        </div>
      ) : isError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">
              Failed to load notifications. {error?.message && `Error: ${error.message}`}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-3 rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        ) : !notifications || notifications.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
            <p className="text-gray-600">
              No notifications yet. Your creator notifications will appear here.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Display notifications in reverse order (latest first) */}
            {notifications && [...notifications].reverse().map((notification) => (
              <div
                key={notification.id}
                className="rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:bg-gray-50"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
                          notification.type === 'solve'
                            ? 'bg-green-100 text-green-800'
                            : notification.type === 'warning'
                            ? 'bg-yellow-100 text-yellow-800'
                            : notification.type === 'ban'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {notification.type === 'solve' ? 'Puzzle Solved' : notification.type === 'warning' ? 'Warning' : notification.type === 'ban' ? 'Account Restriction' : 'Rating'}
                      </span>
                      <span className="text-sm font-medium text-gray-700">
                        {notification.puzzle_name}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-gray-600">
                      {notification.message}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      By {notification.actor_username}
                      {notification.xp_amount > 0 && (
                        <span className="ml-2 font-medium text-green-600">
                          +{notification.xp_amount} XP
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="ml-4 text-right">
                    <p className="text-xs text-gray-500">
                      {new Date(notification.created_at).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-gray-400">
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
