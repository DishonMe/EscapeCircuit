import { api } from '@/lib/api-client';

export type RevealedClue = {
  index: number;
  text: string;
  penalty_seconds: number;
};

export type StartAttemptResponse = {
  id: number;
  puzzle_id: number;
  user_id: number;
  started_at?: string;
  revealed_clues?: RevealedClue[];
  total_clue_penalty_seconds?: number;
};

export const startPuzzleAttempt = ({
  puzzleId,
  restart,
}: {
  puzzleId: string;
  restart?: boolean;
}): Promise<StartAttemptResponse> => {
  const url = restart
    ? `/puzzles/${puzzleId}/attempts/start?restart=true`
    : `/puzzles/${puzzleId}/attempts/start`;
  return api.post(url, undefined, {
    suppressErrorNotification: true,
  });
};
