'use client';

import { useMemo } from 'react';

/**
 * Level formula matching the backend XPService:
 * level = floor(sqrt(xp / 100)) + 1
 *
 * Threshold for level L = (L-1)^2 * 100
 */
export function getLevelInfo(xp: number) {
  const safeXp = Math.max(0, xp);
  const level = Math.floor(Math.sqrt(safeXp / 100)) + 1;

  const currentThreshold = (level - 1) ** 2 * 100;
  const nextThreshold = level ** 2 * 100;

  const xpIntoLevel = safeXp - currentThreshold;
  const xpForLevel = nextThreshold - currentThreshold;
  const pct = xpForLevel > 0 ? Math.min(100, (xpIntoLevel / xpForLevel) * 100) : 100;

  return { level, currentThreshold, nextThreshold, xpIntoLevel, xpForLevel, pct };
}

export const XPBar = ({ currentXP }: { currentXP: number }) => {
  const { level, nextThreshold, pct } = useMemo(
    () => getLevelInfo(currentXP),
    [currentXP],
  );

  return (
    <div className="flex items-center gap-2">
      <span className="whitespace-nowrap text-[11px] font-medium text-muted-foreground">
        Lvl {level}
      </span>
      <div className="relative h-1.5 w-20 overflow-hidden rounded-full bg-secondary sm:w-28">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-foreground/70 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="hidden whitespace-nowrap text-[11px] text-muted-foreground sm:inline">
        {currentXP}/{nextThreshold} XP
      </span>
    </div>
  );
};
