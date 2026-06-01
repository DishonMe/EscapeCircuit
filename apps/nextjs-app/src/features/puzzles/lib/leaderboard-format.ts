/**
 * Pure formatting helpers for the per-puzzle leaderboard (UC1/UC2 — ADD pp.6,11).
 *
 * Extracted from `puzzle-leaderboard.tsx` so the human-readable time/cost
 * formatting can be unit tested without rendering the component.
 */

/** Format a solve time (seconds) as a compact human string: `45s`, `1m 23s`, `1h 2m 3s`. */
export const formatLeaderboardTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${rm}m ${s}s`;
};

/** Format a solve cost for the leaderboard. */
export const formatLeaderboardCost = (cost: number): string => `${cost} cost`;
