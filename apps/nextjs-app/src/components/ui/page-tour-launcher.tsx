"use client";

import { useEffect, useState } from 'react';
import { HelpCircle } from 'lucide-react';

import GuidedTour from '@/components/ui/guided-tour';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/utils/cn';

type PageTourLauncherProps = {
  tourName: string;
  pageTitle: string;
  pageDescription: string;
  steps: any[];
  side?: 'left' | 'right';
  buttonClassName?: string;
};

function TourTooltip({
  index,
  size,
  step,
  backProps,
  primaryProps,
  skipProps,
  tooltipProps,
}: any) {
  const isFirstStep = index === 0;
  const isLastStep = index === size - 1;

  return (
    <div
      {...tooltipProps}
      className="w-[min(92vw,26rem)] rounded-2xl border border-border/70 bg-card/95 p-5 text-card-foreground shadow-2xl backdrop-blur-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Tutorial
          </p>
          <div className="mt-1 text-base font-semibold text-foreground">
            {index + 1}/{size}
          </div>
        </div>
        <div className="rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
          {isLastStep ? 'Final step' : isFirstStep ? 'Start here' : 'Continue'}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-border bg-background/90 p-4 text-sm leading-6 text-foreground shadow-inner">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          What this does
        </div>
        {step?.content}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button variant="ghost" size="sm" {...skipProps} className="px-3 text-sm">
          Skip
        </Button>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            {...backProps}
            disabled={isFirstStep}
            className="px-3 text-sm"
          >
            Prev
          </Button>
          <Button variant="default" size="sm" {...primaryProps} className="px-3 text-sm">
            {isLastStep ? 'Finish' : 'Next'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function PageTourLauncher({
  tourName,
  pageTitle,
  pageDescription,
  steps,
  side = 'right',
  buttonClassName,
}: PageTourLauncherProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [runTour, setRunTour] = useState(false);
  const [tourInstanceId, setTourInstanceId] = useState(0);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const normalizedSteps = (steps || []).map((step: any) => ({
    ...step,
    skipBeacon: true,
  }));

  const handleStartTour = () => {
    setDialogOpen(false);
    setCurrentStepIndex(0);
    setTourInstanceId((current) => current + 1);
    setRunTour(true);
  };

  const handleTourCallback = (data: any) => {
    const { status, index } = data;

    if (typeof index === 'number') {
      setCurrentStepIndex(index);
    }

    if (status === 'finished' || status === 'skipped') {
      setRunTour(false);
    }
  };

  const currentStep = normalizedSteps[currentStepIndex];

  const isInstructionStep =
    typeof currentStep?.target === 'string' && currentStep.target.includes('instructions-button');

  const handleTourAdvanceClick = (event: MouseEvent) => {
    const target = event.target as HTMLElement;
    const isInstructionButtonClick =
      target.closest('.puzzle-instructions-button') || target.closest('.workstation-instructions-button');

    if (!runTour || !isInstructionStep || !isInstructionButtonClick) {
      return;
    }

    window.setTimeout(() => {
      const primaryButton = document.querySelector('[data-action="primary"]') as HTMLButtonElement | null;
      primaryButton?.click();
    }, 120);
  };

  useEffect(() => {
    if (!runTour) {
      return;
    }

    window.addEventListener('click', handleTourAdvanceClick, true);
    return () => window.removeEventListener('click', handleTourAdvanceClick, true);
  }, [runTour, currentStepIndex, normalizedSteps]);

  return (
    <>
      <div
        className={cn(
          'fixed top-12 z-40 sm:top-30',
          side === 'left' ? 'left-4 sm:left-6' : 'right-4 sm:right-6',
        )}
      >
        <Button
          type="button"
          size="icon"
          onClick={() => setDialogOpen(true)}
          aria-label={`Start ${pageTitle} tutorial`}
          className={cn(
            'size-12 rounded-full border-2 border-black bg-white text-black shadow-[0_18px_45px_rgba(0,0,0,0.35)] hover:bg-zinc-100 dark:border-white dark:bg-black dark:text-white dark:hover:bg-zinc-900',
            buttonClassName,
          )}
        >
          <HelpCircle className="size-6" />
        </Button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start tutorial for {pageTitle}?</DialogTitle>
            <DialogDescription>{pageDescription}</DialogDescription>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setDialogOpen(false)}>
              Not now
            </Button>
            <Button type="button" onClick={handleStartTour}>
              Start tutorial
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <GuidedTour
        key={`${tourName}-${tourInstanceId}`}
        steps={normalizedSteps}
        tourName={tourName}
        run={runTour}
        continuous
        scrollToFirstStep={false}
        skipScroll
        showSkipButton={false}
        showProgress={false}
        skipBeacon
        callback={handleTourCallback}
        tooltipComponent={TourTooltip}
        styles={{
          options: {
            primaryColor: 'hsl(var(--foreground))',
            textColor: 'hsl(var(--foreground))',
            backgroundColor: 'hsl(var(--card))',
          },
        }}
        locale={{
          last: 'Finish',
          skip: 'Skip',
          next: 'Next',
          back: 'Previous',
        }}
      />
    </>
  );
}