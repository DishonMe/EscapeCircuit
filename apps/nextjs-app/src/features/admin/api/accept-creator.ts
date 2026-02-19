import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';

export const acceptCreatorRole = () => {
  return api.post('/users/me/accept-creator');
};

type UseAcceptCreatorOptions = {
  mutationConfig?: MutationConfig<typeof acceptCreatorRole>;
};

export const useAcceptCreator = ({
  mutationConfig,
}: UseAcceptCreatorOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: acceptCreatorRole,
  });
};

export const declineCreatorRole = () => {
  return api.post('/users/me/decline-creator');
};

type UseDeclineCreatorOptions = {
  mutationConfig?: MutationConfig<typeof declineCreatorRole>;
};

export const useDeclineCreator = ({
  mutationConfig,
}: UseDeclineCreatorOptions = {}) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: declineCreatorRole,
  });
};
