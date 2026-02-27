'use client';

import NextLink from 'next/link';
import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { paths } from '@/config/paths';
import { DiscussionsList } from '@/features/discussions/components/discussions-list';
import { useUser } from '@/lib/auth';
import { canCreateDiscussion } from '@/lib/authorization';

const DiscussionsPage = () => {
  const user = useUser();

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Discussions</h1>
        {canCreateDiscussion(user.data) && (
          <NextLink href={paths.app.newDiscussion.getHref()}>
            <Button size="sm" icon={<Plus className="size-4" />}>
              New Discussion
            </Button>
          </NextLink>
        )}
      </div>
      <DiscussionsList />
    </div>
  );
};

export default DiscussionsPage;
