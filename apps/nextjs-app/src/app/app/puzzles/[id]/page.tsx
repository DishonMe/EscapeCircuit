import {
  dehydrate,
  HydrationBoundary,
  QueryClient,
} from '@tanstack/react-query';

import { getPuzzleQueryOptions } from '@/features/puzzles/api/get-puzzle';

import { PuzzleWorkstation } from './_components/puzzle-workstation';

export const metadata = {
  title: 'Solve Puzzle',
  description: 'Solve Puzzle',
};

const PuzzleSolvePage = async ({
  params,
}: {
  params: {
    id: string;
  };
}) => {
  const queryClient = new QueryClient();

  await queryClient.prefetchQuery(getPuzzleQueryOptions({ id: params.id }));

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrationBoundary state={dehydratedState}>
      <PuzzleWorkstation puzzleId={params.id} />
    </HydrationBoundary>
  );
};

export default PuzzleSolvePage;
