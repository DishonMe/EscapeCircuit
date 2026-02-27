'use client';

import { useParams } from 'next/navigation';

import { DiscussionView } from '@/features/discussions/components/discussion-view';

const DiscussionPage = () => {
  const params = useParams<{ id: string }>();

  return <DiscussionView discussionId={params.id} />;
};

export default DiscussionPage;
