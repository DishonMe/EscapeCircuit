'use client';

import { Info, CircleAlert, CircleX, CircleCheck } from 'lucide-react';
import { useEffect } from 'react';

const icons = {
  info: <Info className="size-6 text-foreground" aria-hidden="true" />,
  success: (
    <CircleCheck className="size-6 text-emerald-600" aria-hidden="true" />
  ),
  warning: <CircleAlert className="size-6 text-amber-500" aria-hidden="true" />,
  error: <CircleX className="size-6 text-destructive" aria-hidden="true" />,
};

export type NotificationProps = {
  notification: {
    id: string;
    type: keyof typeof icons;
    title: string;
    message?: string;
    persistent?: boolean;
  };
  onDismiss: (id: string) => void;
};

export const Notification = ({
  notification: { id, type, title, message, persistent },
  onDismiss,
}: NotificationProps) => {
  useEffect(() => {
    if (persistent) return;
    const timer = setTimeout(() => {
      onDismiss(id);
    }, 5000);

    return () => clearTimeout(timer);
  }, [id, onDismiss, persistent]);

  return (
    <div className="flex w-full flex-col items-center space-y-4 sm:items-end">
      <div className="pointer-events-auto w-full max-w-sm overflow-hidden rounded-xl border border-border bg-card shadow-elevated">
        <div className="p-4" role="alert" aria-label={title}>
          <div className="flex items-start">
            <div className="shrink-0">{icons[type]}</div>
            <div className="ml-3 w-0 flex-1 pt-0.5">
              <p className="text-[13px] font-medium text-foreground">{title}</p>
              <p className="mt-1 text-[13px] text-muted-foreground">
                {message}
              </p>
            </div>
            <div className="ml-4 flex shrink-0">
              <button
                className="inline-flex rounded-md bg-transparent text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                onClick={() => {
                  onDismiss(id);
                }}
              >
                <span className="sr-only">Close</span>
                <CircleX className="size-5" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
