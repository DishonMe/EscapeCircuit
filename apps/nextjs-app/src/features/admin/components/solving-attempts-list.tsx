
'use client';

import { useMemo, useState } from 'react';
import { Eye } from 'lucide-react';

import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { useSolvingAttempts } from '../api/get-solving-attempts';
import { usePuzzle } from '@/features/puzzles/api/get-puzzle';
import { SolutionPreview } from '@/features/puzzles/components/solution-preview';
import { AdminSolvingAttempt } from '@/types/api';

type Row = AdminSolvingAttempt & { createdAt: number };

export const SolvingAttemptsList = () => {
  const query = useSolvingAttempts({ filters: { limit: 200 } });
  const [selectedAttempt, setSelectedAttempt] = useState<AdminSolvingAttempt | null>(null);
  const puzzleQuery = usePuzzle({
    id: String(selectedAttempt?.puzzle_id ?? ''),
    config: {
      enabled: !!selectedAttempt,
    },
  });

  const rows = useMemo<Row[]>(() => {
    const attempts = query.data?.data ?? [];
    // Filter out attempts with no submitted_structure_json (never actually submitted a circuit)
    return attempts
      .filter((attempt) => attempt.submitted_structure_json !== null && attempt.submitted_structure_json !== undefined && String(attempt.submitted_structure_json).trim() !== '')
      .map((attempt) => {
        const ts = attempt.submitted_at || attempt.started_at;
        return {
          ...attempt,
          createdAt: ts ? new Date(ts).getTime() : 0,
        };
      });
  }, [query.data?.data]);

  const filteredOutCount = useMemo(() => {
    const attempts = query.data?.data ?? [];
    return attempts.filter(
      (attempt) => attempt.submitted_structure_json === null || attempt.submitted_structure_json === undefined || String(attempt.submitted_structure_json).trim() === ''
    ).length;
  }, [query.data?.data]);

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
        <p className="text-[13px] text-red-700">Failed to load solving attempts.</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-secondary p-4">
        <p className="text-foreground/80">No solving attempts yet.</p>
      </div>
    );
  }

  return (
    <>
      {filteredOutCount > 0 && (
        <div className="mb-3 rounded-lg border border-amber-200/60 bg-amber-50/50 p-3">
          <p className="text-[12px] text-amber-700">
            {filteredOutCount} empty attempt{filteredOutCount !== 1 ? 's' : ''} (no circuit) hidden from view
          </p>
        </div>
      )}
      <Table
        data={rows}
        columns={[
          {
            title: 'Result',
            field: 'id',
            Cell({ entry }) {
              const passed = entry.passed === true;
              const failed = entry.passed === false;
              return (
                <span
                  className={`rounded-lg px-2 py-0.5 text-[11px] font-medium ${
                    passed
                      ? 'bg-emerald-50/70 text-emerald-700'
                      : failed
                        ? 'bg-rose-50/70 text-rose-700'
                        : 'bg-secondary text-foreground/70'
                  }`}
                >
                  {passed ? 'Good' : failed ? 'Bad' : 'Open'}
                </span>
              );
            },
          },
          {
            title: 'User',
            field: 'username',
          },
          {
            title: 'Puzzle',
            field: 'puzzle_name',
            Cell({ entry }) {
              return <span>{entry.puzzle_name || `Puzzle #${entry.puzzle_id}`}</span>;
            },
          },
          {
            title: 'Submitted',
            field: 'createdAt',
            Cell({ entry }) {
              const ts = entry.submitted_at || entry.started_at;
              return <span>{ts ? new Date(ts).toLocaleString() : '-'}</span>;
            },
          },
          {
            title: 'Reason',
            field: 'id',
            Cell({ entry }) {
              if (entry.passed === true) {
                return <span className="text-xs text-emerald-600 font-medium">Passed</span>;
              }
              return <span className={`text-xs ${entry.passed === false ? 'text-rose-600 font-medium' : 'text-muted-foreground'}`}>{entry.fail_reason || '-'}</span>;
            },
          },
          {
            title: 'Board',
            field: 'id',
            Cell({ entry }) {
              return (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedAttempt(entry)}
                >
                  <Eye className="mr-1 size-4" />
                  Open
                </Button>
              );
            },
          },
        ]}
      />

      <Dialog open={!!selectedAttempt} onOpenChange={(open) => !open && setSelectedAttempt(null)}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Submitted Board</DialogTitle>
            <DialogDescription>
              Attempt #{selectedAttempt?.id} by {selectedAttempt?.username}
            </DialogDescription>
          </DialogHeader>

          {!selectedAttempt?.submitted_structure_json ? (
            <div className="rounded-lg border border-border bg-secondary p-3 text-sm text-muted-foreground">
              No submitted board is stored for this attempt. This can happen when the
              attempt was opened but never submitted.
            </div>
          ) : (
            <SolutionPreview
              puzzle={puzzleQuery.data ?? null}
              payload={selectedAttempt.submitted_structure_json}
              loadingMessage="Loading puzzle context for this attempt..."
              emptyMessage="No submitted board is stored for this attempt."
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
