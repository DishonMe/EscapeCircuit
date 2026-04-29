'use client';

import { Lightbulb } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/dialog/confirmation-dialog';
import { useNotifications } from '@/components/ui/notifications';
import {
  useRequestClue,
  type RequestClueResponse,
} from '@/features/puzzles/api/request-clue';

export type RevealedClue = {
  index: number;
  text: string;
  penalty: number;
};

export type ClueButtonProps = {
  puzzleId: string | number;
  attemptId: number | null;
  totalClues: number;
  cluePenaltySeconds: number;
  hasCountdown?: boolean;
  revealedClues: RevealedClue[];
  onClueRevealed: (clue: RevealedClue) => void;
};

export const ClueButton = ({
  puzzleId,
  attemptId,
  totalClues,
  cluePenaltySeconds,
  hasCountdown = false,
  revealedClues,
  onClueRevealed,
}: ClueButtonProps) => {
  const { addNotification } = useNotifications();
  const requestClue = useRequestClue();
  const [pendingRequestId, setPendingRequestId] = useState<string | null>(null);
  const [confirmDoneTick, setConfirmDoneTick] = useState(0);

  if (totalClues <= 0) return null;

  const used = revealedClues.length;
  const allUsed = used >= totalClues;
  const disabled =
    attemptId === null ||
    requestClue.isPending ||
    pendingRequestId !== null ||
    allUsed;

  const handleConfirm = async () => {
    if (attemptId === null) return;
    const requestId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setPendingRequestId(requestId);
    try {
      const response: RequestClueResponse = await requestClue.mutateAsync({
        puzzleId,
        attemptId,
        requestId,
      });
      // `replayed` only means the server has already charged this request_id
      // (e.g. our previous POST succeeded but its response was lost). The local
      // UI may still be missing this clue, so hydrate it if absent. Only the
      // user-facing toast is gated on "fresh" so a retry doesn't double-fire it.
      const newClue: RevealedClue = {
        index: response.clue_index,
        text: response.clue_text,
        penalty: response.penalty_seconds,
      };
      const alreadyShown = revealedClues.some((c) => c.index === newClue.index);
      if (!alreadyShown) {
        onClueRevealed(newClue);
      }
      if (!response.replayed && !alreadyShown) {
        const message = hasCountdown
          ? `−${response.penalty_seconds}s on your countdown and +${response.penalty_seconds}s on your time taken. Total clue penalty: ${response.total_penalty_so_far}s.`
          : `+${response.penalty_seconds}s added to your time taken. Total clue penalty: ${response.total_penalty_so_far}s.`;
        addNotification({
          type: 'warning',
          title: 'Clue revealed — penalty applied',
          message,
        });
      }
      setConfirmDoneTick((t) => t + 1);
    } catch (err) {
      addNotification({
        type: 'error',
        title: 'Could not reveal clue',
        message: err instanceof Error ? err.message : 'Please try again.',
      });
      setConfirmDoneTick((t) => t + 1);
    } finally {
      setPendingRequestId(null);
    }
  };

  const nextNumber = used + 1;
  const dialogBody = allUsed
    ? 'No more clues left for this puzzle.'
    : hasCountdown
      ? `This will subtract ${cluePenaltySeconds}s from your live countdown AND add ${cluePenaltySeconds}s to your recorded time taken (medals & leaderboard). (Clue ${nextNumber} of ${totalClues} — penalty stacks on each clue.)`
      : `This will add ${cluePenaltySeconds}s to your time taken. (Clue ${nextNumber} of ${totalClues} — penalty stacks on each clue.)`;

  return (
    <div className="flex flex-col gap-2">
      <ConfirmationDialog
        title="Reveal next clue?"
        body={dialogBody}
        cancelButtonText="Cancel"
        icon="danger"
        isDone={confirmDoneTick > 0}
        triggerButton={
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            className="gap-1.5"
          >
            <Lightbulb className="size-4" aria-hidden />
            <span>
              {allUsed ? 'All clues used' : `Clues (${used}/${totalClues})`}
            </span>
          </Button>
        }
        confirmButton={
          <Button
            type="button"
            variant="destructive"
            disabled={disabled || allUsed}
            onClick={handleConfirm}
          >
            {requestClue.isPending
              ? 'Revealing…'
              : `Reveal clue (+${cluePenaltySeconds}s)`}
          </Button>
        }
      />

      {revealedClues.length > 0 ? (
        <div className="rounded-md border border-amber-200/70 bg-amber-50/60 p-2 text-xs text-amber-900">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
            Revealed clues
          </div>
          <ol className="list-decimal space-y-1 pl-4">
            {revealedClues
              .slice()
              .sort((a, b) => a.index - b.index)
              .map((c) => (
                <li key={c.index}>
                  <span>{c.text}</span>
                  <span className="ml-1 text-[10px] text-amber-700">
                    (+{c.penalty}s)
                  </span>
                </li>
              ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
};
