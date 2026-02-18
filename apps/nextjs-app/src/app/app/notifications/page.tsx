'use client';

import { useRouter } from 'next/navigation';
import { Loader } from 'lucide-react';

import { useUser } from '@/lib/auth';
import { useCreatorNotificationsHistory } from '@/features/notifications/api';

const NotificationsPage = () => {
  const user = useUser();
  const router = useRouter();
  const { data: notifications, isLoading, isError, error, refetch } = useCreatorNotificationsHistory();

  // Only allow creators and admins to view this page
  const userRole = user.data?.role?.toLowerCase() || '';
  if (user.status === 'success' && userRole !== 'creator' && userRole !== 'admin') {
    router.push('/app');
    return null;
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        <p className="mt-2 text-gray-600">
          View all your creator notifications in one place
        </p>
      </div>

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
            {[...notifications].reverse().map((notification) => (
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
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {notification.type === 'solve' ? 'Puzzle Solved' : 'Rating'}
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
