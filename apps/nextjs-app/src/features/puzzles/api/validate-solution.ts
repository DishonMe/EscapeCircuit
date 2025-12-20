import { api } from '@/lib/api-client';
import { CircuitSolution } from '@/types/api';

export type ValidateSolutionRequest = {
  solution: CircuitSolution;
};

export type ValidateSolutionResponse = {
  solved: boolean;
  message: string;
};

export const validateSolution = ({
  puzzleId,
  solution,
}: {
  puzzleId: string;
  solution: CircuitSolution;
}): Promise<ValidateSolutionResponse> => {
  return api.post(`/puzzles/${puzzleId}/validate`, { solution });
};
