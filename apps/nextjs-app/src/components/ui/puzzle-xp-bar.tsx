'use client';

import { useMemo } from 'react';
import { calculateMaxXP, calculateMaxXPFromTier, getDifficultyTier } from '@/utils/xp-utils';

interface PuzzleXPBarProps {
  avgDifficulty?: number;
  /** Creator-set difficulty tier (EASY/MEDIUM/HARD). When provided, max XP is
   *  derived from this fixed value so community ratings cannot change it. */
  difficulty?: string;
  currentXP?: number;
}

/**
 * Display bar showing max XP achievable on a puzzle and current earned XP
 */
export const PuzzleXPBar = ({ avgDifficulty = 0, difficulty, currentXP = 0 }: PuzzleXPBarProps) => {
  const xpInfo = useMemo(() => {
    // Use creator-set difficulty tier for max XP so ratings don't change it.
    // Fall back to avg_difficulty-based calculation if tier is not provided.
    const maxXP = difficulty ? calculateMaxXPFromTier(difficulty) : calculateMaxXP(avgDifficulty);
    const displayCurrent = Math.max(0, currentXP);
    const percentage = maxXP > 0 ? (displayCurrent / maxXP) * 100 : 0;
    // Tier colour still reflects community rating for visual feedback.
    const tier = difficulty ? (difficulty.toUpperCase() as 'EASY' | 'MEDIUM' | 'HARD') : getDifficultyTier(avgDifficulty);

    return {
      maxXP,
      displayCurrent,
      percentage,
      tier,
    };
  }, [avgDifficulty, difficulty, currentXP]);

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
