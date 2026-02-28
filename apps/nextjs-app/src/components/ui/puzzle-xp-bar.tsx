'use client';

import { useMemo } from 'react';
import { calculateMaxXP, getDifficultyTier } from '@/utils/xp-utils';

interface PuzzleXPBarProps {
  avgDifficulty?: number;
  currentXP?: number;
  isSolved?: boolean;
}

/**
 * Display bar showing max XP achievable on a puzzle and current earned XP
 */
export const PuzzleXPBar = ({ avgDifficulty = 0, currentXP = 0, isSolved = false }: PuzzleXPBarProps) => {
  const xpInfo = useMemo(() => {
    const maxXP = calculateMaxXP(avgDifficulty);
    const displayCurrent = isSolved ? currentXP : 0;
    const percentage = maxXP > 0 ? (displayCurrent / maxXP) * 100 : 0;
    const tier = getDifficultyTier(avgDifficulty);

    return {
      maxXP,
      displayCurrent,
      percentage,
      tier,
    };
  }, [avgDifficulty, currentXP, isSolved]);

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'EASY':
        return 'bg-green-500';
      case 'MEDIUM':
        return 'bg-yellow-500';
      case 'HARD':
        return 'bg-red-500';
      default:
        return 'bg-foreground/30';
    }
  };

  return (
    <div className="w-full space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-foreground">Max XP</span>
        <span className="font-medium text-muted-foreground">
          {xpInfo.displayCurrent}/{xpInfo.maxXP}
        </span>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${getTierColor(xpInfo.tier)}`}
          style={{ width: `${Math.min(100, xpInfo.percentage)}%` }}
        />
      </div>
    </div>
  );
};
