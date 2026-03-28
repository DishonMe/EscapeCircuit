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
  
  // Log the prefetched puzzle data to verify arsenalComponents are included
  const cachedData = queryClient.getQueryData(['puzzle', { id: params.id }]);
  if (cachedData) {
    const puzzle = cachedData as any;
    console.log("\n📦 SERVER [page.tsx]: Prefetched puzzle data:");
    console.log("   - id:", puzzle.id);
    console.log("   - title:", puzzle.title);
    console.log("   - arsenalComponents count:", (puzzle.arsenalComponents || []).length);
    console.log("   - customComponents count:", (puzzle.customComponents || []).length);
    
    if (puzzle.arsenalComponents && puzzle.arsenalComponents.length > 0) {
      console.log("\n   First Arsenal Component:");
      const first = puzzle.arsenalComponents[0];
      console.log("   - id:", first.id);
      console.log("   - type:", first.type);
      console.log("   - description key present:", 'description' in first);
      console.log("   - description value:", first.description);
      console.log("   - all keys:", Object.keys(first));
      console.log("   - full object:", JSON.stringify(first, null, 2));
    }
  } else {
    console.log("⚠️ No cached data found!");
  }

  const dehydratedState = dehydrate(queryClient);

  return (
    <HydrationBoundary state={dehydratedState}>
      <PuzzleWorkstation puzzleId={params.id} />
    </HydrationBoundary>
  );
};

export default PuzzleSolvePage;
