'use client';

import { Spinner } from '@/components/ui/spinner';

import { useAuthAttempts } from '../api/get-auth-attempts';

const actionLabel: Record<string, string> = {
  login: 'Login',
  register: 'Register',
  login_google: 'Google Login',
  register_google: 'Google Register',
};

export const AuthAttemptsList = () => {
  const query = useAuthAttempts({ filters: { limit: 200 } });

  if (query.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="rounded-lg border border-red-200/60 bg-red-50/50 p-4">
        <p className="text-[13px] text-red-700">
          Failed to load login/register logs.
        </p>
      </div>
    );
  }

  const entries = query.data || [];

  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-secondary p-4">
        <p className="text-foreground/80">No login/register attempts yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="rounded-xl border border-border bg-card p-3 text-[13px]"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-foreground">
                {actionLabel[entry.action] || entry.action}
              </span>
              <span
                className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${
                  entry.success
                    ? 'bg-emerald-50/70 text-emerald-700'
                    : 'bg-rose-50/70 text-rose-700'
                }`}
              >
                {entry.success ? 'Success' : 'Failed'}
              </span>
            </div>
            <span className="text-[11px] text-foreground/70">
              {new Date(entry.created_at).toLocaleString()}
            </span>
          </div>

          <div className="mt-1.5 text-foreground/80">
            {entry.username_or_email ? entry.username_or_email : 'Unknown user'}
            {entry.user_id ? <span> (user #{entry.user_id})</span> : null}
          </div>

          {entry.reason ? (
            <div className="mt-1 text-[11px] text-foreground/70">
              Reason: {entry.reason}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
};
