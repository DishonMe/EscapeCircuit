import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';

import { getDiscussionQueryOptions } from './get-discussion';

export const viewDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{ view_count: number }> => {
  return api.post(`/discussions/${discussionId}/view`);
};

export const useViewDiscussion = ({ discussionId }: { discussionId: string }) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: viewDiscussion,
    onSuccess: (data) => {
      // Update the cached discussion with the new view_count so the UI shows +1 immediately
      queryClient.setQueryData(
        getDiscussionQueryOptions(discussionId).queryKey,
        (old: any) => {
          if (!old) return old;
          return { ...old, view_count: data.view_count };
        },
      );
    },
  });
};
