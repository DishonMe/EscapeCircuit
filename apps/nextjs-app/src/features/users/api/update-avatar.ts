import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api-client';
import { useUser } from '@/lib/auth';
import { MutationConfig } from '@/lib/react-query';

export const updateAvatarInputSchema = z.object({
  avatar_name: z.string().min(1, 'Avatar is required'),
  avatar_color: z.string().regex(/^#[0-9A-F]{6}$/i, 'Invalid color format'),
});

export type UpdateAvatarInput = z.infer<typeof updateAvatarInputSchema>;

export const updateAvatar = ({ data }: { data: UpdateAvatarInput }) => {
  return api.patch(`/users/avatar`, data);
};

type UseUpdateAvatarOptions = {
  mutationConfig?: MutationConfig<typeof updateAvatar>;
};

export const useUpdateAvatar = ({
  mutationConfig,
}: UseUpdateAvatarOptions = {}) => {
  const queryClient = useQueryClient();
  const { refetch: refetchUser } = useUser();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      refetchUser();
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: updateAvatar,
  });
};
