"use client";

import { useState } from 'react';
import { CircleHelp } from 'lucide-react';

import GuidedTour from '@/components/ui/guided-tour';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
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

  const storageKey = `escapecircuit.tour.${tourName}.completed`;

  const handleStartTour = () => {
    setDialogOpen(false);
    setRunTour(true);
  };

  const handleTourCallback = (data: any) => {
    const { status } = data;

    if (status === 'finished' || status === 'skipped') {
      localStorage.setItem(storageKey, 'true');
      setRunTour(false);
    }
  };

  return (
    <>
      <div
        className={cn(
          'fixed top-12 z-40 sm:top-30',
          side === 'left' ? 'left-4 sm:left-6' : 'right-4 sm:right-6',
        )}
      >
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          aria-label={`Open ${pageTitle} tutorial`}
          className={cn(
            'flex size-14 items-center justify-center rounded-full bg-foreground text-background shadow-[0_18px_45px_rgba(0,0,0,0.35)] transition-transform duration-200 hover:scale-105 hover:bg-foreground/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background',
            buttonClassName,
          )}
        >
          <CircleHelp className="size-7" aria-hidden="true" />
          <span className="sr-only">Open tutorial</span>
        </button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start {pageTitle} tutorial?</DialogTitle>
            <DialogDescription>{pageDescription}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Not now
            </Button>
            <Button onClick={handleStartTour}>Start tutorial</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <GuidedTour
        steps={steps}
        tourName={tourName}
        run={runTour}
        continuous
        scrollToFirstStep
        showSkipButton={false}
        showProgress={false}
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