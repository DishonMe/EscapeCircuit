'use client';

import { useCallback } from 'react';

import { PageTourLauncher } from '@/components/ui/page-tour-launcher';
import { myPuzzlesTourSteps } from '@/config/tour-steps';
import { useCompleteTutorial } from '@/features/users/api/complete-tutorial';

import { MyPuzzles } from './my-puzzles';

export const MyPuzzlesClient = ({ autoStartTutorial = false }: { autoStartTutorial?: boolean }) => {
  const { mutate: completeTutorial } = useCompleteTutorial({});

  const handleTourFinished = useCallback(() => {
    console.log('[MyPuzzlesClient] handleTourFinished called, about to call completeTutorial');
    completeTutorial('my-puzzles');
  }, [completeTutorial]);

  return (
    <div className="relative">
      <MyPuzzles
        tutorialSlot={
          <PageTourLauncher
            tourName="my-puzzles"
            pageTitle="My Puzzles"
            pageDescription="Get a quick walkthrough of your puzzle tabs, actions, and creation entry point."
            steps={myPuzzlesTourSteps}
            disableScrolling
            floating={false}
            inlineLabel="Tutorial"
            autoStart={autoStartTutorial}
            onTourFinished={handleTourFinished}
          />
        }
      />
    </div>
  );
};
