'use client';

import { useMemo } from 'react';

const formatTime = (seconds: number) => {
  const abs = Math.abs(seconds);
  const m = Math.floor(abs / 60);
  const s = abs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
};

/**
 * The clue penalty is added to displayed elapsed time in both modes — for the
 * countdown case it shrinks the visible remaining time, for the no-limit case
 * it inflates the visible elapsed. In the no-limit case we also append a
 * compact "+Ns" pill inside the timer so the user can see how much of the
 * displayed time is penalty. For the countdown case the breakdown is
 * surfaced separately by `puzzle-workstation` (a dedicated "Time-taken
 * penalty" pill alongside the timer) — that pill makes it explicit that the
 * same penalty is also recorded on the leaderboard.
 */
export const WorkstationTimer = ({
  elapsedSeconds,
  extraSeconds = 0,
  timeLimitSeconds,
}: {
  elapsedSeconds: number;
  extraSeconds?: number;
  timeLimitSeconds?: number | null;
}) => {
  const penalty = Math.max(0, Math.floor(extraSeconds || 0));
  const displayElapsed = Math.max(0, Math.floor(elapsedSeconds || 0)) + penalty;
  const hasLimit = typeof timeLimitSeconds === 'number' && timeLimitSeconds > 0;

  const { label, colorClass } = useMemo(() => {
    if (!hasLimit) {
      return {
        label: formatTime(displayElapsed),
        colorClass: 'bg-slate-50/50 text-slate-700 border-slate-200/60',
      };
    }

    const remaining = (timeLimitSeconds as number) - displayElapsed;

    if (remaining <= 0) {
      return {
        label: `+${formatTime(remaining)}`,
        colorClass: 'bg-red-50/50 text-red-700 border-red-200/60',
      };
    }

    const percentage = remaining / (timeLimitSeconds as number);
    let color = 'bg-emerald-50/50 text-emerald-700 border-emerald-200/60';
    if (percentage <= 0.1) {
      color = 'bg-amber-50/50 text-amber-700 border-amber-200/60';
    }

    return { label: formatTime(remaining), colorClass: color };
  }, [hasLimit, displayElapsed, timeLimitSeconds]);

  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[13px] font-medium backdrop-blur-sm transition-colors duration-300 ${colorClass}`}
    >
      <span>
        <span className="mr-1 opacity-60">Time:</span>
        <span className="font-semibold tabular-nums tracking-tight">
          {label}
        </span>
      </span>
      {!hasLimit && penalty > 0 ? (
        <span
          className="rounded bg-red-100/80 px-1.5 py-0.5 text-[11px] font-semibold text-red-700"
          title="Penalty added for clues"
        >
          +{penalty}s
        </span>
      ) : null}
    </div>
  );
};
