'use client';

import { PageTourLauncher } from '@/components/ui/page-tour-launcher';
import { myPuzzlesTourSteps } from '@/config/tourSteps';
import { MyPuzzles } from './my-puzzles';

export const MyPuzzlesClient = () => {
  return (
    <>
      <PageTourLauncher
        tourName="my-puzzles"
        pageTitle="My Puzzles"
        pageDescription="Get a quick walkthrough of your puzzle tabs, actions, and creation entry point."
        steps={myPuzzlesTourSteps}
        side="left"
      />
      <div className="relative">
        <MyPuzzles />
      </div>
    </>
  );
};
