import { describe, expect, it } from 'vitest';

import {
  formatLeaderboardCost,
  formatLeaderboardTime,
} from '../leaderboard-format';

/**
 * ADD pp.6,11 — per-puzzle leaderboard (PuzzleLeaderboard) displays solve time
 * and cost in human-readable form. This pins that formatting.
 */
describe('formatLeaderboardTime', () => {
  it('shows bare seconds under a minute', () => {
    expect(formatLeaderboardTime(0)).toBe('0s');
    expect(formatLeaderboardTime(45)).toBe('45s');
  });

  it('shows minutes and seconds under an hour', () => {
    expect(formatLeaderboardTime(60)).toBe('1m 0s');
    expect(formatLeaderboardTime(83)).toBe('1m 23s');
  });

  it('shows hours, minutes and seconds at or above an hour', () => {
    expect(formatLeaderboardTime(3723)).toBe('1h 2m 3s');
  });
});

describe('formatLeaderboardCost', () => {
  it('suffixes the cost with " cost"', () => {
    expect(formatLeaderboardCost(15)).toBe('15 cost');
  });
});
