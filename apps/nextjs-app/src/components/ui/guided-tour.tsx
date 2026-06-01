'use client';

import { usePathname } from 'next/navigation';
import React, { useEffect, useState, useLayoutEffect } from 'react';

export default function GuidedTour({ steps, ...props }: any) {
  const [JoyrideComponent, setJoyrideComponent] = useState<any>(null);
  const pathname = usePathname();
  const [active, setActive] = useState(true);

  // 1. Instant Kill on Path Change
  useLayoutEffect(() => {
    setActive(false);
    const timer = setTimeout(() => setActive(true), 300);
    return () => {
      setActive(false);
      clearTimeout(timer);
    };
  }, [pathname]);

  // 2. Global Event Listener: Kill tour on navigation link clicks, but NOT Joyride button clicks
  useEffect(() => {
    const handleGlobalClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;

      // 1. Check if the click happened inside a Joyride tooltip or beacon
      const isJoyrideClick =
        target.closest('.react-joyride__tooltip') ||
        target.closest('.react-joyride__beacon');

      // 2. Only kill the tour if it's a navigation-related link click NOT inside Joyride
      if (!isJoyrideClick && target.closest('a')) {
        setActive(false);
      }
    };

    window.addEventListener('click', handleGlobalClick, { capture: true });
    return () => window.removeEventListener('click', handleGlobalClick);
  }, []);

  useEffect(() => {
    import('react-joyride')
      .then((module: any) => {
        const Component = module.default || (module as any).Joyride || module;
        setJoyrideComponent(() => Component);
      })
      .catch((err) => console.error('Failed to load react-joyride', err));
  }, []);

  // Return null immediately if not active or not loaded
  if (!JoyrideComponent || !active) return null;

  const fixedSteps =
    steps?.map((step: any) => ({
      ...step,
      skipBeacon: step.skipBeacon ?? props.skipBeacon ?? true,
    })) || [];

  const mergedStyles = {
    ...(props.styles || {}),
    options: {
      ...((props.styles && props.styles.options) || {}),
      zIndex: 10020,
    },
  };

  return (
    <JoyrideComponent
      {...props}
      steps={fixedSteps}
      run={props.run && active}
      skipBeacon={true}
      styles={mergedStyles}
    />
  );
}
