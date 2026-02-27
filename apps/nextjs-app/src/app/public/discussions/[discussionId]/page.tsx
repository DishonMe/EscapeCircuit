'use client';

import { useParams } from 'next/navigation';

import { DiscussionView } from '@/features/discussions/components/discussion-view';

const PublicDiscussionPage = () => {
  const params = useParams<{ discussionId: string }>();

  return <DiscussionView discussionId={params.discussionId} />;
};

export default PublicDiscussionPage;
