'use client';

import { PageTourLauncher } from '@/components/ui/page-tour-launcher';
import {
  PuzzlesList,
  puzzlesTourSteps,
} from '@/features/puzzles/components/puzzles-list';
import { PuzzlesPageHeader } from '@/features/puzzles/components/puzzles-page-header';

export const Puzzles = () => {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Low-opacity dotted grid — contained within the page, not fixed */}
      <div className="relative">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 opacity-[0.04]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 2px 2px, hsl(var(--foreground)) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <PuzzlesPageHeader
          tutorialSlot={
            <PageTourLauncher
              tourName="browse-puzzles"
              pageTitle="Circuit Puzzles"
              pageDescription="Learn how to filter, sort, and open a puzzle to start solving. You can reopen this guide any time from the Tutorial button."
              steps={puzzlesTourSteps}
              disableScrolling
              floating={false}
              inlineLabel="Tutorial"
            />
          }
        />
        <PuzzlesList />
      </div>
    </div>
  );
};
