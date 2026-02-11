'use client';

import { useMemo } from 'react';

/**
 * Level thresholds matching the backend XPService.
 * Index = level (1-based), value = minimum XP for that level.
 */
const LEVEL_THRESHOLDS = [0, 250, 600, 1100, 1700, 2000, 2600, 3400, 4500, 6000];

function getLevelInfo(xp: number) {
  let level = 1;
  for (let i = 0; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) {
      level = i + 1;
    }
  }

  const currentThreshold = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const nextThreshold =
    level < LEVEL_THRESHOLDS.length
      ? LEVEL_THRESHOLDS[level]
      : LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1] + 2000; // beyond max

  const xpIntoLevel = xp - currentThreshold;
  const xpForLevel = nextThreshold - currentThreshold;
  const pct = xpForLevel > 0 ? Math.min(100, (xpIntoLevel / xpForLevel) * 100) : 100;

  return { level, currentThreshold, nextThreshold, pct };
}

export const XPBar = ({ currentXP }: { currentXP: number }) => {
  const { level, nextThreshold, pct } = useMemo(
    () => getLevelInfo(currentXP),
    [currentXP],
  );

  return (
    <div className="flex items-center gap-2">
      <span className="whitespace-nowrap text-xs font-semibold text-gray-700">
        Lvl {level}
      </span>
      <div className="relative h-2 w-24 overflow-hidden rounded-full bg-gray-200 sm:w-32">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-blue-600 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="hidden whitespace-nowrap text-xs text-gray-500 sm:inline">
        {currentXP}/{nextThreshold} XP
      </span>
    </div>
  );
};
