import { api } from '@/lib/api-client';
import { CircuitSolution } from '@/types/api';

export type ValidateSolutionRequest = {
  solution: CircuitSolution;
  time_taken?: number;
};

export type ValidateSolutionResponse = {
  solved: boolean;
  message: string;
  xp_earned?: number;
  time_taken?: number;
  medal?: 'NONE' | 'BRONZE' | 'SILVER' | 'GOLD';
  medal_value?: number;
};

export const validateSolution = ({
  puzzleId,
  solution,
  timeTaken,
}: {
  puzzleId: string;
  solution: CircuitSolution;
  timeTaken?: number;
}): Promise<ValidateSolutionResponse> => {
  return api.post(`/puzzles/${puzzleId}/validate`, {
    solution,
    time_taken: timeTaken ?? 0,
  }, { suppressErrorNotification: true });
};
