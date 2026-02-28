'use client';

import { useEffect, useMemo, useState } from 'react';

const formatTime = (seconds: number) => {
  const abs = Math.abs(seconds);
  const m = Math.floor(abs / 60);
  const s = abs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
};

export const WorkstationTimer = ({
  timeLimitSeconds,
}: {
  timeLimitSeconds?: number | null;
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 250);

    return () => window.clearInterval(interval);
  }, []);

  const hasLimit = typeof timeLimitSeconds === 'number' && timeLimitSeconds > 0;
  // If no limit, we can treat remaining as infinite or calculate differently.
  // For logic preservation, we define remaining based on limit if exists.
  const remaining = hasLimit ? (timeLimitSeconds as number) - elapsed : 0;

  const { label, colorClass } = useMemo(() => {
    if (!hasLimit) return { label: null, colorClass: '' };

    // Overtime
    if (remaining <= 0) {
      return { 
        label: `+${formatTime(remaining)}`, 
        colorClass: 'bg-red-50/50 text-red-700 border-red-200/60'
      };
    }

    // Normal countdown
    const percentage = remaining / (timeLimitSeconds as number);
    let color = 'bg-emerald-50/50 text-emerald-700 border-emerald-200/60'; // Default Green ( > 10%)

    if (percentage <= 0.1) {
      color = 'bg-amber-50/50 text-amber-700 border-amber-200/60'; // Yellow ( <= 10%)
    }

    return { label: formatTime(remaining), colorClass: color };
  }, [hasLimit, remaining, timeLimitSeconds]);

  if (!label) return null;

  return (
    <div className={`rounded-lg border px-3 py-1.5 text-[13px] font-medium backdrop-blur-sm transition-colors duration-300 ${colorClass}`}>
      <span className="opacity-60 mr-1">Time:</span>
      <span className="font-semibold tabular-nums tracking-tight">{label}</span>
    </div>
  );
};
