import { useMutation } from '@tanstack/react-query';

import { api } from '@/lib/api-client';

export type RequestClueRequest = {
  puzzleId: string | number;
  attemptId: number;
  requestId: string;
};

export type RequestClueResponse = {
  clue_index: number;
  clue_text: string;
  penalty_seconds: number;
  total_clues: number;
  clues_used_so_far: number;
  total_penalty_so_far: number;
  replayed: boolean;
};

export const requestClue = ({
  puzzleId,
  attemptId,
  requestId,
}: RequestClueRequest): Promise<RequestClueResponse> => {
  return api.post(
    `/puzzles/${puzzleId}/clue`,
    {
      attempt_id: attemptId,
      request_id: requestId,
    },
    { suppressErrorNotification: true },
  );
};

export const useRequestClue = () =>
  useMutation({
    mutationFn: requestClue,
  });
