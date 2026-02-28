'use client';

import { useRouter } from 'next/navigation';
import { Loader } from 'lucide-react';

import { useUser } from '@/lib/auth';
import { useCreatorNotificationsHistory } from '@/features/notifications/api';

const NotificationsPage = () => {
  const user = useUser();
  const router = useRouter();

  const { data: notifications, isLoading, isError, error, refetch } = useCreatorNotificationsHistory({
    filters: { limit: 10, orderBy: 'created_at', orderDirection: 'DESC' },
  });

  // Only allow creators and admins to view this page
  const userRole = user.data?.role?.toLowerCase() || '';
  if (user.status === 'success' && userRole !== 'creator' && userRole !== 'admin') {
    router.push('/app');
    return null;
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Notifications</h1>
        <p className="mt-2 text-[13px] text-muted-foreground">
          Your 10 most recent notifications
        </p>
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
