'use client';

import { useRouter } from 'next/navigation';

import { paths } from '@/config/paths';

import { CreateDiscussion } from '@/features/discussions/components/create-discussion';

const NewDiscussionPage = () => {
  const router = useRouter();

  return (
    <div className="mx-auto w-full max-w-3xl">
      <CreateDiscussion
        onSuccess={(discussion) => {
          router.push(paths.app.discussion.getHref(String(discussion.id)));
        }}
      />
    </div>
  );
};

export default NewDiscussionPage;
