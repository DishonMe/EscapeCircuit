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
  timeLimitSeconds: number;
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 250);

    return () => window.clearInterval(interval);
  }, []);

  const remaining = timeLimitSeconds - elapsed;

  const label = useMemo(() => {
    if (remaining >= 0) return formatTime(remaining);
    return `+${formatTime(remaining)}`;
  }, [remaining]);

  return (
    <div className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900">
      <span className="font-medium">Time:</span> {label}
    </div>
  );
};
