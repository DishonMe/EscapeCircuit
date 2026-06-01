/**
 * Pure helpers for the WorkStation countdown timer's visual state.
 *
 * Extracted from `workstation-timer.tsx` so the "timer visual cues" behaviour
 * promised in the ADD (Chapter 7.4 — Usability: Timer Visual Cues) can be unit
 * tested in isolation, with no React rendering:
 *
 *   • green (normal)  while remaining time is > 10% of the limit
 *   • amber (warning) once remaining time is <= 10% of the limit
 *   • red (expired)   at zero and below — label flips to a "+" stopwatch that
 *     counts up
 *   • slate (no-limit) when the puzzle has no time limit (elapsed counts up)
 */
export type TimerState = 'no-limit' | 'normal' | 'warning' | 'expired';

/** Format a (possibly negative) second count as `M:SS` (sign handled by caller). */
export const formatCountdown = (seconds: number): string => {
  const abs = Math.abs(seconds);
  const m = Math.floor(abs / 60);
  const s = abs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
};

/**
 * Compute the timer's visual state + display label from the already-adjusted
 * elapsed time (i.e. elapsed + any clue penalty) and the puzzle time limit.
 */
export const timerVisualState = (
  displayElapsedSeconds: number,
  timeLimitSeconds: number | null | undefined,
): { state: TimerState; label: string; remaining: number | null } => {
  const hasLimit = typeof timeLimitSeconds === 'number' && timeLimitSeconds > 0;

  if (!hasLimit) {
    return {
      state: 'no-limit',
      label: formatCountdown(displayElapsedSeconds),
      remaining: null,
    };
  }

  const limit = timeLimitSeconds as number;
  const remaining = limit - displayElapsedSeconds;

  if (remaining <= 0) {
    return {
      state: 'expired',
      label: `+${formatCountdown(remaining)}`,
      remaining,
    };
  }

  const percentage = remaining / limit;
  const state: TimerState = percentage <= 0.1 ? 'warning' : 'normal';
  return { state, label: formatCountdown(remaining), remaining };
};
