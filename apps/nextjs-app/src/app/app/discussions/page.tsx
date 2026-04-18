'use client';

import NextLink from 'next/link';
import { MessageSquare, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { PageHero } from '@/components/ui/page-hero/page-hero';
import { paths } from '@/config/paths';
import { DiscussionsList } from '@/features/discussions/components/discussions-list';
import { useUser } from '@/lib/auth';
import { canCreateDiscussion } from '@/lib/authorization';

const DiscussionsPage = () => {
  const user = useUser();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-4">
      <PageHero
        badge="Community"
        icon={MessageSquare}
        title="Discussions"
        description="Trade solutions, compare approaches, and share ideas with the rest of the circuit-solving community."
        rightSlot={
          canCreateDiscussion(user.data) && (
            <NextLink href={paths.app.newDiscussion.getHref()}>
              <Button size="sm" icon={<Plus className="size-4" />}>
                New Discussion
              </Button>
            </NextLink>
          )
        }
      />
      <DiscussionsList />
    </div>
  );
};

export default DiscussionsPage;
