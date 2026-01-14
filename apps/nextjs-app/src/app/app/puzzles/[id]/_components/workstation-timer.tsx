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
        colorClass: 'bg-red-50 text-red-700 border-red-200' 
      };
    }

    // Normal countdown
    const percentage = remaining / (timeLimitSeconds as number);
    let color = 'bg-green-50 text-green-700 border-green-200'; // Default Green ( > 10%)

    if (percentage <= 0.1) {
      color = 'bg-yellow-50 text-yellow-700 border-yellow-200'; // Yellow ( <= 10%)
    }

    return { label: formatTime(remaining), colorClass: color };
  }, [hasLimit, remaining, timeLimitSeconds]);

  if (!label) return null;

  return (
    <div className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors duration-300 ${colorClass}`}>
      <span className="opacity-70 mr-1">Time:</span>
      <span className="font-bold tabular-nums">{label}</span>
    </div>
  );
};
