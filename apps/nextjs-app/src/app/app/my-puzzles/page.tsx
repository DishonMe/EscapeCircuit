import {
  dehydrate,
  HydrationBoundary,
  QueryClient,
} from '@tanstack/react-query';

import { getPuzzlesQueryOptions } from '@/features/puzzles/api/get-puzzles';

import { MyPuzzlesClient } from './_components/my-puzzles-client';

export const metadata = {
  title: 'My Created Puzzles',
  description: 'View and manage your created circuit puzzles',
};

const MyPuzzlesPage = async ({
  searchParams,
}: {
  searchParams: { page: string | null; startTutorial?: string };
}) => {
  const queryClient = new QueryClient();

  await queryClient.prefetchQuery(
    getPuzzlesQueryOptions({
      page: searchParams.page ? Number(searchParams.page) : 1,
    }),
  );

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrationBoundary state={dehydratedState}>
      <MyPuzzlesClient autoStartTutorial={searchParams.startTutorial === 'true'} />
    </HydrationBoundary>
  );
};

export default MyPuzzlesPage;
