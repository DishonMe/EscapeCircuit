'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  Ban,
  Lock,
  Trash2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog';
import { useNotifications } from '@/components/ui/notifications';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/utils/cn';

import { useReports } from '../api/get-reports';
import {
  useBanReportAuthor,
  useDeleteReportedContent,
  useLockReportedDiscussion,
  useWarnReportAuthor,
} from '../api/report-actions';
import { useUpdateReportStatus } from '../api/update-report-status';

const formatDate = (dateStr: string) => {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
};

const reasonLabels: Record<string, string> = {
  spam: 'Spam',
  harassment: 'Harassment',
  off_topic: 'Off Topic',
  inappropriate: 'Inappropriate',
  other: 'Other',
};

const reasonColors: Record<string, string> = {
  spam: 'bg-red-50 text-red-700',
  harassment: 'bg-red-100 text-red-800',
  off_topic: 'bg-yellow-50 text-yellow-700',
  inappropriate: 'bg-orange-50 text-orange-700',
  other: 'bg-gray-50 text-gray-700',
};

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-50 text-yellow-700',
  reviewed: 'bg-green-50 text-green-700',
  dismissed: 'bg-gray-100 text-gray-500',
};

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'dismissed', label: 'Dismissed' },
] as const;

export const ReportsList = () => {
  const [statusFilter, setStatusFilter] = useState('');
  const query = useReports({ status: statusFilter || undefined });
  const updateMutation = useUpdateReportStatus();
  const { addNotification } = useNotifications();

  const warnMutation = useWarnReportAuthor({
    mutationConfig: {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Warning sent to author' });
      },
    },
  });

  const banMutation = useBanReportAuthor({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'Author banned from discussions',
        });
      },
    },
  });

  const deleteMutation = useDeleteReportedContent({
    mutationConfig: {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Reported content deleted' });
      },
    },
  });

  const lockMutation = useLockReportedDiscussion({
    mutationConfig: {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Discussion locked' });
      },
    },
  });

  if (query.isLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">Failed to load reports.</p>
      </div>
    );
  }

  const reports = query.data?.reports || [];

  return (
    <div className="space-y-3">
      {/* Status filter tabs */}
      <div className="flex gap-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              statusFilter === f.value
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {reports.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <p className="text-gray-600">
            {statusFilter
              ? `No ${statusFilter} reports.`
              : 'No reports yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {reports.map((report) => (
            <div
              key={report.id}
              className="rounded-lg border border-gray-200 bg-white p-3 text-sm"
            >
              {/* Top row: reason badge, status badge, date */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      reasonColors[report.reason] || 'bg-gray-50 text-gray-700'
                    }`}
                  >
                    {reasonLabels[report.reason] || report.reason}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      statusColors[report.status] ||
                      'bg-gray-50 text-gray-700'
                    }`}
                  >
                    {report.status}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {formatDate(report.created_at)}
                </span>
              </div>

              {/* Content info: target link, reporter, author */}
              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-gray-600">
                <span className="font-medium capitalize">
                  {report.target_type}
                </span>
                <Link
                  href={`/app/discussions/${report.target_type === 'discussion' ? report.target_id : ''}`}
                  className="text-blue-600 hover:underline"
                >
                  #{report.target_id}
                </Link>
                {report.target_author_username && (
                  <>
                    <span className="text-gray-300">|</span>
                    <span className="text-xs">
                      Author:{' '}
                      <span className="font-medium">
                        {report.target_author_username}
                      </span>
                    </span>
                  </>
                )}
                <span className="text-gray-300">|</span>
                <span className="text-xs">
                  Reporter:{' '}
                  <span className="font-medium">
                    {report.reporter_username || `#${report.reporter_id}`}
                  </span>
                </span>
              </div>

              {report.details && (
                <div className="mt-1 text-xs text-gray-400">
                  {report.details}
                </div>
              )}

              {/* Actions for pending reports */}
              {report.status === 'pending' && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {/* Status actions */}
                  <button
                    onClick={() =>
                      updateMutation.mutate({
                        reportId: report.id,
                        status: 'reviewed',
                      })
                    }
                    disabled={updateMutation.isPending}
                    className="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
                  >
                    Mark Reviewed
                  </button>
                  <button
                    onClick={() =>
                      updateMutation.mutate({
                        reportId: report.id,
                        status: 'dismissed',
                      })
                    }
                    disabled={updateMutation.isPending}
                    className="rounded bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                  >
                    Dismiss
                  </button>

                  <span className="mx-1 border-l border-gray-200" />

                  {/* Moderation actions */}
                  <button
                    onClick={() =>
                      warnMutation.mutate({ reportId: report.id })
                    }
                    disabled={warnMutation.isPending}
                    className="flex items-center gap-1 rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                  >
                    <AlertTriangle className="size-3" />
                    Warn Author
                  </button>

                  {report.target_type === 'discussion' && (
                    <button
                      onClick={() =>
                        lockMutation.mutate({ reportId: report.id })
                      }
                      disabled={lockMutation.isPending}
                      className="flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                    >
                      <Lock className="size-3" />
                      Lock
                    </button>
                  )}

                  <ConfirmationDialog
                    icon="danger"
                    title="Delete Reported Content"
                    body={`Permanently delete this ${report.target_type}? This action cannot be undone.`}
                    triggerButton={
                      <button className="flex items-center gap-1 rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100">
                        <Trash2 className="size-3" />
                        Delete Content
                      </button>
                    }
                    confirmButton={
                      <Button
                        isLoading={deleteMutation.isPending}
                        type="button"
                        variant="destructive"
                        onClick={() =>
                          deleteMutation.mutate({ reportId: report.id })
                        }
                      >
                        Delete
                      </Button>
                    }
                  />

                  <ConfirmationDialog
                    icon="danger"
                    title="Ban Author from Discussions"
                    body={`Ban ${report.target_author_username || 'this user'} from creating discussions and replies?`}
                    triggerButton={
                      <button className="flex items-center gap-1 rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100">
                        <Ban className="size-3" />
                        Ban Author
                      </button>
                    }
                    confirmButton={
                      <Button
                        isLoading={banMutation.isPending}
                        type="button"
                        variant="destructive"
                        onClick={() =>
                          banMutation.mutate({ reportId: report.id })
                        }
                      >
                        Ban User
                      </Button>
                    }
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
