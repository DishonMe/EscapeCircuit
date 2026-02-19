'use client';

import { Spinner } from '@/components/ui/spinner';
import { useAuditLog } from '../api/get-audit-log';

const formatAuditDate = (dateStr: string) => {
  try {
    const d = new Date(dateStr);
    return d.toLocaleString();
  } catch {
    return dateStr;
  }
};

const actionTypeLabels: Record<string, string> = {
  assign_creator: 'Assigned Creator',
  remove_creator: 'Removed Creator',
  delete_puzzle: 'Deleted Puzzle',
  unpublish_puzzle: 'Unpublished Puzzle',
};

const actionTypeColors: Record<string, string> = {
  assign_creator: 'bg-blue-50 text-blue-700',
  remove_creator: 'bg-orange-50 text-orange-700',
  delete_puzzle: 'bg-red-50 text-red-700',
  unpublish_puzzle: 'bg-yellow-50 text-yellow-700',
};

export const AuditLogList = () => {
  const query = useAuditLog({});

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
        <p className="text-sm text-red-700">Failed to load audit log.</p>
      </div>
    );
  }

  const entries = query.data || [];

  if (entries.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <p className="text-gray-600">No audit log entries yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="rounded-lg border border-gray-200 bg-white p-3 text-sm"
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className={`rounded px-2 py-0.5 text-xs font-medium ${
                actionTypeColors[entry.action_type] ||
                'bg-gray-50 text-gray-700'
              }`}
            >
              {actionTypeLabels[entry.action_type] ||
                entry.action_type.replace(/_/g, ' ')}
            </span>
            <span className="text-xs text-gray-500">
              {formatAuditDate(entry.created_at)}
            </span>
          </div>
          <div className="mt-1.5 text-gray-600">
            <span>Admin #{entry.admin_user_id}</span>
            {entry.target_user_id && (
              <span> &rarr; User #{entry.target_user_id}</span>
            )}
            {entry.target_puzzle_id && (
              <span> &rarr; Puzzle #{entry.target_puzzle_id}</span>
            )}
          </div>
          {entry.details && Object.keys(entry.details).length > 0 && (
            <div className="mt-1 text-xs text-gray-400">
              {Object.entries(entry.details).map(([key, value]) => (
                <span key={key} className="mr-3">
                  {key.replace(/_/g, ' ')}: {String(value)}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
