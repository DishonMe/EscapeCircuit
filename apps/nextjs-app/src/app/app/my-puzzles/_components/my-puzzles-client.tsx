'use client';

import { useState, useEffect } from 'react';
import GuidedTour from '@/components/ui/guided-tour';
import { myPuzzlesTourSteps } from '@/config/tourSteps';
import { Button } from '@/components/ui/button';
import { MyPuzzles } from './my-puzzles';

export const MyPuzzlesClient = () => {
  const [runTour, setRunTour] = useState(false);

  // Auto-start tour on first visit
  useEffect(() => {
    const tourCompleted = localStorage.getItem('escapecircuit.tour.my-puzzles.status');
    if (!tourCompleted) {
      setRunTour(true);
    }
  }, []);

  const handleTourCallback = (data: any) => {
    const { action, type, status } = data;
    // Mark tour as completed when user finishes or skips
    if (status === 'finished' || status === 'skipped') {
      localStorage.setItem('escapecircuit.tour.my-puzzles.status', 'completed');
      setRunTour(false);
    }
  };

  return (
    <>
      <GuidedTour
        steps={myPuzzlesTourSteps}
        tourName="my-puzzles"
        run={runTour}
        callback={handleTourCallback}
      />
      <div className="relative">
        <MyPuzzles />
      </div>
    </>
  );
};
