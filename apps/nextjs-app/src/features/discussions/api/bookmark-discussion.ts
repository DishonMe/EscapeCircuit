import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { MutationConfig } from '@/lib/react-query';
import { Discussion, Reply } from '@/types/api';

import { getDiscussionQueryOptions } from './get-discussion';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

type DiscussionsListResponse = {
  discussions: Discussion[];
  total: number;
  limit: number;
  offset: number;
};

const sortBookmarkedFirst = (discussions: Discussion[]): Discussion[] => {
  return [...discussions].sort(
    (a, b) =>
      Number(Boolean(b.is_bookmarked)) - Number(Boolean(a.is_bookmarked)),
  );
};

export const toggleBookmark = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<{
  discussion_id: number;
  is_bookmarked: boolean;
}> => {
  return api.post(`/discussions/${discussionId}/bookmark`);
};

type UseToggleBookmarkOptions = {
  discussionId: string;
  mutationConfig?: MutationConfig<typeof toggleBookmark>;
};

export const useToggleBookmark = ({
  discussionId,
  mutationConfig,
}: UseToggleBookmarkOptions) => {
  const queryClient = useQueryClient();

  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    ...restConfig,
    mutationFn: toggleBookmark,
    onMutate: async () => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      await queryClient.cancelQueries({ queryKey });
      const previous =
        queryClient.getQueryData<DiscussionWithReplies>(queryKey);

      await queryClient.cancelQueries({ queryKey: ['discussions'] });
      const previousLists = queryClient.getQueriesData<DiscussionsListResponse>(
        {
          queryKey: ['discussions'],
        },
      );

      let nextIsBookmarked: boolean | undefined;

      if (previous?.engagement) {
        nextIsBookmarked = !previous.engagement.is_bookmarked;
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...previous,
          is_bookmarked: !previous.engagement.is_bookmarked,
          engagement: {
            ...previous.engagement,
            is_bookmarked: !previous.engagement.is_bookmarked,
          },
        });
      }

      for (const [key, listData] of previousLists) {
        if (!listData?.discussions?.length) continue;

        const target = listData.discussions.find(
          (d) => String(d.id) === String(discussionId),
        );
        const resolvedNext =
          nextIsBookmarked ?? (target ? !target.is_bookmarked : undefined);
        if (resolvedNext === undefined) continue;
        nextIsBookmarked = resolvedNext;

        const updatedDiscussions = listData.discussions.map((d) =>
          String(d.id) === String(discussionId)
            ? { ...d, is_bookmarked: resolvedNext }
            : d,
        );

        const keyParts = Array.isArray(key) ? key : [];
        const filters =
          keyParts.length > 1 &&
          typeof keyParts[1] === 'object' &&
          keyParts[1] !== null
            ? (keyParts[1] as { bookmarkedOnly?: boolean })
            : undefined;
        const bookmarkedOnly = Boolean(filters?.bookmarkedOnly);

        let nextDiscussions = updatedDiscussions;
        let nextTotal = listData.total;

        if (bookmarkedOnly && resolvedNext === false) {
          const before = nextDiscussions.length;
          nextDiscussions = nextDiscussions.filter(
            (d) => String(d.id) !== String(discussionId),
          );
          if (before > nextDiscussions.length) {
            nextTotal = Math.max(0, nextTotal - 1);
          }
        }

        queryClient.setQueryData<DiscussionsListResponse>(key, {
          ...listData,
          discussions: sortBookmarkedFirst(nextDiscussions),
          total: nextTotal,
        });
      }

      return { previous, previousLists };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          getDiscussionQueryOptions(discussionId).queryKey,
          context.previous,
        );
      }
      for (const [key, data] of context?.previousLists || []) {
        queryClient.setQueryData(key, data);
      }
    },
    onSuccess: (data, ...rest) => {
      const queryKey = getDiscussionQueryOptions(discussionId).queryKey;
      const current = queryClient.getQueryData<DiscussionWithReplies>(queryKey);
      if (current?.engagement) {
        queryClient.setQueryData<DiscussionWithReplies>(queryKey, {
          ...current,
          is_bookmarked: data.is_bookmarked,
          engagement: {
            ...current.engagement,
            is_bookmarked: data.is_bookmarked,
          },
        });
      }
      queryClient.invalidateQueries({ queryKey: ['discussions'] });
      onSuccess?.(data, ...rest);
    },
  });
};

// Backward-compatible aliases.
export const bookmarkDiscussion = toggleBookmark;
export const useBookmarkDiscussion = useToggleBookmark;
