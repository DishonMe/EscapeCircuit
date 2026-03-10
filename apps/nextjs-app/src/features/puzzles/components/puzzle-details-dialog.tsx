'use client';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Link } from '@/components/ui/link';
import type { Puzzle } from '@/types/api';

type PuzzleDetailsDialogProps = {
  puzzle: Puzzle | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  showLink?: boolean;
};

export const PuzzleDetailsDialog = ({
  puzzle,
  open,
  onOpenChange,
  showLink = true,
}: PuzzleDetailsDialogProps) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{puzzle?.title ?? 'Puzzle details'}</DialogTitle>
          <DialogDescription>
            Key information before you start solving.
          </DialogDescription>
        </DialogHeader>

        {puzzle ? (
          <div className="max-h-[60vh] space-y-3 overflow-y-auto text-sm text-gray-700">
            <div>
              <div className="font-medium text-gray-900">Description</div>
              <div className="mt-1 whitespace-pre-wrap">
                {puzzle.description}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2 rounded border border-gray-200 bg-gray-50 p-3 text-sm sm:grid-cols-2">
              <div>
                <span className="font-medium text-gray-900">Time:</span>{' '}
                {Math.floor(puzzle.timeLimit / 60)}m{' '}
                {(puzzle.timeLimit % 60).toString().padStart(2, '0')}s
              </div>
              <div>
                <span className="font-medium text-gray-900">Budget:</span>{' '}
                {puzzle.budgetLimit}
              </div>
              <div>
                <span className="font-medium text-gray-900">Creator&apos;s Cost:</span>{' '}
                {puzzle.creatorBudget ?? puzzle.tightBudgetLimit ?? '—'}
              </div>
            </div>

            <div>
              <div className="font-medium text-gray-900">
                Additional constraints (optional)
              </div>
              <div className="mt-1 space-y-1">
                {Array.isArray(puzzle.additionalConstraints) ? (
                  puzzle.additionalConstraints.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5">
                      {puzzle.additionalConstraints.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-gray-500">None provided.</div>
                  )
                ) : puzzle.additionalConstraints ? (
                  <div>{puzzle.additionalConstraints}</div>
                ) : (
                  <div className="text-gray-500">None provided.</div>
                )}
              </div>
            </div>

            {puzzle.creatorComment ? (
              <div>
                <div className="font-medium text-gray-900">Creator comment</div>
                <div className="mt-1 whitespace-pre-wrap">
                  {puzzle.creatorComment}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {showLink && puzzle ? (
            <Link
              href={`/app/puzzles/${puzzle.id}`}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Go to puzzle
            </Link>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
