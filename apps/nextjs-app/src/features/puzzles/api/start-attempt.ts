import { api } from '@/lib/api-client';

export type StartAttemptResponse = {
  id: number;
  puzzle_id: number;
  user_id: number;
  started_at?: string;
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
