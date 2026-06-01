import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';

export const completeTutorial = (tutorialName: string): Promise<any> => {
  console.log(`[completeTutorial API] Sending request for tutorial: ${tutorialName}`);
  return api.post(`/users/me/complete-tutorial`, { tutorial_name: tutorialName });
};

type UseCompleteTutorialOptions = {
  onSuccess?: () => void;
};

export const useCompleteTutorial = ({
  onSuccess,
}: UseCompleteTutorialOptions = {}) => {
  const queryClient = useQueryClient();

  return useMutation<any, Error, string>({
    mutationFn: (tutorialName: string) => {
      console.log(`[useCompleteTutorial] Mutation called with: ${tutorialName}`);
      return completeTutorial(tutorialName);
    },
    onSuccess: (data) => {
      console.log(`[useCompleteTutorial] Success response:`, data);
      // Invalidate user query to refresh tutorials_completed status and XP
      queryClient.invalidateQueries({ queryKey: ['user'] });
      onSuccess?.();
    },
    onError: (error) => {
      console.error(`[useCompleteTutorial] Error:`, error);
    },
  });
};
