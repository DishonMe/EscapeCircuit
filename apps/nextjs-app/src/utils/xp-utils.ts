/**
 * XP utility functions matching backend XPService logic
 */

// Base XP per difficulty tier (from backend XPService)
const BASE_XP = {
  EASY: 50,
  MEDIUM: 100,
  HARD: 200,
};

// Medal bonuses (from backend XPService)
const MEDAL_BONUS = {
  NONE: 0,
  BRONZE: 0,
  SILVER: 25,
  GOLD: 50,
};

/**
 * Determine difficulty tier from average difficulty rating
 * Matches backend: tier_from_avg_difficulty
 */
export function getDifficultyTier(avgDifficulty: number): 'EASY' | 'MEDIUM' | 'HARD' {
  const d = typeof avgDifficulty === 'number' ? avgDifficulty : 0;
  if (d >= 7.0) {
    return 'HARD';
  }
  if (d >= 4.0) {
    return 'MEDIUM';
  }
  return 'EASY';
}

/**
 * Calculate the maximum XP a user can earn on a puzzle (Gold medal)
 * Max XP = base XP for difficulty + Gold medal bonus
 */
export function calculateMaxXP(avgDifficulty: number): number {
  const tier = getDifficultyTier(avgDifficulty);
  const baseXP = BASE_XP[tier] || 0;
  const goldBonus = MEDAL_BONUS.GOLD || 0;
  return baseXP + goldBonus;
}

/**
 * Get the XP range (min and max) for a puzzle
 */
export function getXPRange(avgDifficulty: number) {
  const tier = getDifficultyTier(avgDifficulty);
  const baseXP = BASE_XP[tier] || 0;
  const minXP = baseXP + MEDAL_BONUS.BRONZE; // Bronze medal
  const maxXP = baseXP + MEDAL_BONUS.GOLD; // Gold medal
  return { minXP, maxXP };
}

/**
 * Get difficulty display info
 */
export function getDifficultyInfo(avgDifficulty: number) {
  const tier = getDifficultyTier(avgDifficulty);
  const { minXP, maxXP } = getXPRange(avgDifficulty);

  return {
    tier,
    minXP,
    maxXP,
    rating: avgDifficulty,
  };
}
