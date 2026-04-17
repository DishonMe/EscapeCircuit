"use client";

import { useEffect, useRef, useState } from 'react';
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
  /** Disable Joyride's auto-scroll between steps. Use when every target is already visible. */
  disableScrolling?: boolean;
  /** Pixels of clearance between the top of the viewport and the target after scroll. */
  scrollOffset?: number;
  /** When false, render the trigger inline (no fixed positioning). Default: true. */
  floating?: boolean;
  /** Label shown next to the icon when rendered inline. */
  inlineLabel?: string;
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
  disableScrolling = false,
  scrollOffset = 140,
  floating = true,
  inlineLabel = 'Tutorial',
}: PageTourLauncherProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [runTour, setRunTour] = useState(false);
  const [tourInstanceId, setTourInstanceId] = useState(0);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Captured originals of scroll APIs the freeze useEffect neutralises — let us
  // perform explicit, opt-in scrolls from step:before even while the freeze is
  // active (so focus() / Joyride can't move the page, but we still can).
  const scrollApisRef = useRef<{
    elementScrollIntoView: typeof Element.prototype.scrollIntoView;
  } | null>(null);

  const normalizedSteps = (steps || []).map((step: any) => {
    const isDialogCloseStep =
      typeof step.target === 'string' && step.target.includes('dialog-close-button');

    return {
      ...step,
      skipBeacon: true,
      // Open the instructions dialog before showing the close-button step
      ...(isDialogCloseStep && {
        after: () => {
          const closeBtn = document.querySelector(step.target) as HTMLElement | null;
          if (closeBtn) {
            closeBtn.click();
          }
        },
        before: () =>
          new Promise<void>((resolve) => {
            // If the dialog is already open, proceed immediately
            if (document.querySelector(step.target)) {
              resolve();
              return;
            }
            // Click the instructions button to open the dialog
            const instructionsBtn = (
              document.querySelector('.puzzle-instructions-button') ??
              document.querySelector('.workstation-instructions-button')
            ) as HTMLElement | null;
            if (instructionsBtn) {
              instructionsBtn.click();
            }
            // Wait for the dialog close button to appear in the DOM, then
            // allow the dialog open animation to finish before resolving
            const observer = new MutationObserver(() => {
              if (document.querySelector(step.target)) {
                observer.disconnect();
                setTimeout(resolve, 350);
              }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            // Safety timeout so the tour doesn't hang forever
            setTimeout(() => {
              observer.disconnect();
              resolve();
            }, 2000);
          }),
      }),
    };
  });

  const handleStartTour = () => {
    setDialogOpen(false);
    setCurrentStepIndex(0);
    setTourInstanceId((current) => current + 1);
    // Take the user to the top before the tour starts. When `disableScrolling`
    // is set, the scroll-freeze effect kicks in once runTour=true, so we scroll
    // FIRST (while scroll is still allowed) and then engage the tour after the
    // smooth scroll has had time to land.
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    }
    window.setTimeout(() => setRunTour(true), 500);
  };

  const handleTourCallback = (data: any) => {
    const { status, index, type, step } = data;

    if (typeof index === 'number') {
      setCurrentStepIndex(index);
    }

    // Center off-screen targets ourselves — but ONLY when the step explicitly opts in
    // via `scrollIntoView: true`. Auto-scrolling on every step causes overscroll when a
    // later step's target is already in view after an earlier scroll.
    if (type === 'step:before' && step?.scrollIntoView === true) {
      const scrollSelector =
        typeof step.scrollTarget === 'string'
          ? step.scrollTarget
          : typeof step.target === 'string'
            ? step.target
            : null;
      if (scrollSelector) {
        requestAnimationFrame(() => {
          const el = document.querySelector(
            scrollSelector,
          ) as HTMLElement | null;
          if (!el) return;
          // When the freeze is active, the prototype scrollIntoView is a noop —
          // use the captured original so opt-in scrolls still land.
          const scrollFn =
            scrollApisRef.current?.elementScrollIntoView ??
            Element.prototype.scrollIntoView;
          scrollFn.call(el, { block: 'center', behavior: 'smooth' });
        });
      }
    }

    if (status === 'finished' || status === 'skipped') {
      setRunTour(false);
    }
  };

  const currentStep = normalizedSteps[currentStepIndex];

  const isInstructionStep =
    typeof currentStep?.target === 'string' && currentStep.target.includes('instructions-button');

  const handleTourAdvanceClick = (event: MouseEvent) => {
    // Ignore programmatic clicks (e.g. from the before hook opening the dialog)
    if (!event.isTrusted) return;

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

  // When a page opts into `disableScrolling`, make sure NOTHING moves the scroll
  // position for the duration of the tour: not Joyride, not focus changes, not the
  // Radix dialog that opens for the dialog-close step.
  //
  // We do this proactively (no-op the programmatic scroll APIs) so the scroll never
  // happens in the first place — a reactive "snap back" would render visibly laggy.
  // User-initiated scrolls (wheel / touch / keys) go through the browser's native
  // scroll pipeline, not these APIs, so they're unaffected.
  useEffect(() => {
    if (!runTour || !disableScrolling) return;

    // 1. Patch focus() so any focus() call during the tour passes preventScroll:true.
    const originalFocus = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function patchedFocus(options) {
      return originalFocus.call(this, { ...(options || {}), preventScroll: true });
    };

    // 2. Neutralise programmatic scroll methods on Window and Element.
    const originalWindowScrollTo = window.scrollTo;
    const originalWindowScrollBy = window.scrollBy;
    const originalWindowScroll = window.scroll;
    const originalElementScrollIntoView = Element.prototype.scrollIntoView;
    const originalElementScrollTo = Element.prototype.scrollTo;
    const originalElementScrollBy = Element.prototype.scrollBy;
    const originalElementScroll = Element.prototype.scroll;

    const noop = () => {};
    (window as unknown as { scrollTo: typeof noop }).scrollTo = noop;
    (window as unknown as { scrollBy: typeof noop }).scrollBy = noop;
    (window as unknown as { scroll: typeof noop }).scroll = noop;
    (Element.prototype as unknown as { scrollIntoView: typeof noop }).scrollIntoView = noop;
    (Element.prototype as unknown as { scrollTo: typeof noop }).scrollTo = noop;
    (Element.prototype as unknown as { scrollBy: typeof noop }).scrollBy = noop;
    (Element.prototype as unknown as { scroll: typeof noop }).scroll = noop;

    // Hand the originals to the step:before callback so it can still scroll
    // for steps that explicitly opt in (`scrollIntoView: true`).
    scrollApisRef.current = {
      elementScrollIntoView: originalElementScrollIntoView,
    };

    // 3. Intercept direct `scrollTop` / `scrollLeft` setter assignments on the
    //    page's scrolling element — this is the path Joyride uses for its animated
    //    scroll (it writes `scrollTop = n` inside a rAF loop). Overriding the
    //    setter on the instance (not the prototype) keeps overflow:auto child
    //    containers — e.g. scrollable content inside a dialog — fully functional.
    const scrollEl =
      (document.scrollingElement as HTMLElement | null) ?? document.documentElement;
    const bodyEl = document.body;

    const scrollTopProto = Object.getOwnPropertyDescriptor(
      Element.prototype,
      'scrollTop',
    );
    const scrollLeftProto = Object.getOwnPropertyDescriptor(
      Element.prototype,
      'scrollLeft',
    );

    const freeze = (el: HTMLElement) => {
      if (!scrollTopProto?.get || !scrollLeftProto?.get) return;
      Object.defineProperty(el, 'scrollTop', {
        configurable: true,
        get() {
          return scrollTopProto.get!.call(this);
        },
        set() {
          /* blocked during tour */
        },
      });
      Object.defineProperty(el, 'scrollLeft', {
        configurable: true,
        get() {
          return scrollLeftProto.get!.call(this);
        },
        set() {
          /* blocked during tour */
        },
      });
    };

    const unfreeze = (el: HTMLElement) => {
      // Deleting the instance-level property restores prototype access.
      delete (el as unknown as { scrollTop?: number }).scrollTop;
      delete (el as unknown as { scrollLeft?: number }).scrollLeft;
    };

    freeze(scrollEl);
    if (bodyEl !== scrollEl) freeze(bodyEl);

    return () => {
      HTMLElement.prototype.focus = originalFocus;
      (window as unknown as { scrollTo: typeof originalWindowScrollTo }).scrollTo =
        originalWindowScrollTo;
      (window as unknown as { scrollBy: typeof originalWindowScrollBy }).scrollBy =
        originalWindowScrollBy;
      (window as unknown as { scroll: typeof originalWindowScroll }).scroll =
        originalWindowScroll;
      (
        Element.prototype as unknown as {
          scrollIntoView: typeof originalElementScrollIntoView;
        }
      ).scrollIntoView = originalElementScrollIntoView;
      (
        Element.prototype as unknown as { scrollTo: typeof originalElementScrollTo }
      ).scrollTo = originalElementScrollTo;
      (
        Element.prototype as unknown as { scrollBy: typeof originalElementScrollBy }
      ).scrollBy = originalElementScrollBy;
      (
        Element.prototype as unknown as { scroll: typeof originalElementScroll }
      ).scroll = originalElementScroll;
      unfreeze(scrollEl);
      if (bodyEl !== scrollEl) unfreeze(bodyEl);
      scrollApisRef.current = null;
    };
  }, [runTour, disableScrolling]);

  return (
    <>
      {floating ? (
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
      ) : (
        <Button
          type="button"
          variant="ghost"
          onClick={() => setDialogOpen(true)}
          aria-label={`Start ${pageTitle} tutorial`}
          className={cn(
            'group h-auto gap-2 rounded-full border border-border/70 bg-card/70 px-4 py-2 text-sm font-semibold text-foreground shadow-sm backdrop-blur-sm transition-all hover:border-primary/50 hover:bg-primary/10 hover:text-foreground hover:shadow-md',
            buttonClassName,
          )}
        >
          <span className="flex size-6 items-center justify-center rounded-full bg-primary/15 text-primary transition-colors group-hover:bg-primary/25">
            <HelpCircle className="size-4" />
          </span>
          {inlineLabel}
        </Button>
      )}

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
        disableScrolling={true}
        scrollOffset={scrollOffset}
        showSkipButton={false}
        showProgress={false}
        skipBeacon
        onEvent={handleTourCallback}
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