import { api } from '@/lib/api-client';
import { CircuitSolution } from '@/types/api';

export type ValidateSolutionRequest = {
  solution: CircuitSolution;
  time_taken?: number;
  time_taken_raw?: number;
  attempt_id?: number;
};

export type ValidateSolutionResponse = {
  solved: boolean;
  message: string;
  xp_earned?: number;
  puzzle_total_xp?: number;
  xp_left_for_max?: number;
  time_taken?: number;
  medal?: 'NONE' | 'BRONZE' | 'SILVER' | 'GOLD';
  medal_value?: number;
};

export const validateSolution = ({
  puzzleId,
  solution,
  timeTaken,
  attemptId,
}: {
  puzzleId: string;
  solution: CircuitSolution;
  timeTaken?: number;
  attemptId?: number | null;
}): Promise<ValidateSolutionResponse> => {
  return api.post(
    `/puzzles/${puzzleId}/validate`,
    {
      solution,
      // Send under the new field name; server treats time_taken_raw as the source of truth
      // and adds persisted clue penalty server-side. Legacy time_taken is kept for callers
      // that haven't migrated yet.
      time_taken: timeTaken ?? 0,
      time_taken_raw: timeTaken ?? 0,
      attempt_id: attemptId ?? undefined,
    },
    { suppressErrorNotification: true },
  );
};
