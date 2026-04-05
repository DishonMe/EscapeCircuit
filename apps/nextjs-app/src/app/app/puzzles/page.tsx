import {
  dehydrate,
  HydrationBoundary,
  QueryClient,
} from '@tanstack/react-query';

import { getPuzzlesQueryOptions } from '@/features/puzzles/api/get-puzzles';
import GuidedTour from '@/components/ui/guided-tour';
import { browsePuzzlesTourSteps } from '@/config/tourSteps';

import { Puzzles } from './_components/puzzles';

export const metadata = {
  title: 'Circuit Puzzles',
  description: 'Browse and solve circuit design puzzles',
};

const PuzzlesPage = async ({
  searchParams,
}: {
  searchParams: { page: string | null };
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
      <GuidedTour
        steps={browsePuzzlesTourSteps}
        tourName="browse-puzzles"
      />
      <Puzzles />
    </HydrationBoundary>
  );
};

export default PuzzlesPage;
