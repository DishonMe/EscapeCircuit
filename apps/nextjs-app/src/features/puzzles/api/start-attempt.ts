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
}: {
  puzzleId: string;
}): Promise<StartAttemptResponse> => {
  return api.post(`/puzzles/${puzzleId}/attempts/start`, undefined, {
    suppressErrorNotification: true,
  });
};
