import { useQuery, queryOptions } from '@tanstack/react-query';

import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Discussion, Reply } from '@/types/api';

type DiscussionWithReplies = Discussion & {
  replies: (Reply & { children?: Reply[] })[];
};

export const getDiscussion = ({
  discussionId,
}: {
  discussionId: string;
}): Promise<DiscussionWithReplies> => {
  return api.get(`/discussions/${discussionId}`);
};

export const getDiscussionQueryOptions = (discussionId: string) => {
  return queryOptions({
    queryKey: ['discussions', discussionId],
    queryFn: () => getDiscussion({ discussionId }),
    refetchInterval: 1000 * 15, // poll every 15s for new replies
  });
};

type UseDiscussionOptions = {
  discussionId: string;
  queryConfig?: QueryConfig<typeof getDiscussionQueryOptions>;
};

export const useDiscussion = ({
  discussionId,
  queryConfig,
}: UseDiscussionOptions) => {
  return useQuery({
    ...getDiscussionQueryOptions(discussionId),
    ...queryConfig,
  });
};
