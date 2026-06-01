import { describe, expect, it } from 'vitest';

import { isPlausibleStartedAt } from '../timer';

const NOW = Date.parse('2026-01-15T12:00:00Z');

describe('isPlausibleStartedAt', () => {
  it('accepts "just now"', () => {
    expect(isPlausibleStartedAt(NOW, NOW, 60)).toBe(true);
  });

  it('accepts an elapsed time within 4x the time limit for timed puzzles', () => {
    // 60s puzzle -> 240s threshold. 3 minutes ago is still inside.
    const threeMinutesAgo = NOW - 3 * 60 * 1000;
    expect(isPlausibleStartedAt(threeMinutesAgo, NOW, 60)).toBe(true);
  });

  it('rejects an elapsed time past 4x the time limit for timed puzzles', () => {
    // 60s puzzle -> 240s threshold. 30 minutes ago is well past.
    const thirtyMinutesAgo = NOW - 30 * 60 * 1000;
    expect(isPlausibleStartedAt(thirtyMinutesAgo, NOW, 60)).toBe(false);
  });

  it('accepts up to 24h for no-limit puzzles', () => {
    const tenHoursAgo = NOW - 10 * 3600 * 1000;
    expect(isPlausibleStartedAt(tenHoursAgo, NOW, null)).toBe(true);
  });

  it('rejects beyond 24h regardless of time limit', () => {
    const sevenDaysAgo = NOW - 7 * 24 * 3600 * 1000;
    expect(isPlausibleStartedAt(sevenDaysAgo, NOW, null)).toBe(false);
    expect(isPlausibleStartedAt(sevenDaysAgo, NOW, 60)).toBe(false);
  });

  it('caps the timed-puzzle bound at 24h even when time_limit * 4 > 24h', () => {
    // 10h limit -> raw bound would be 40h, but the cap clamps to 24h.
    const twentyHoursAgo = NOW - 20 * 3600 * 1000;
    expect(isPlausibleStartedAt(twentyHoursAgo, NOW, 10 * 3600)).toBe(true);
    const twentyFiveHoursAgo = NOW - 25 * 3600 * 1000;
    expect(isPlausibleStartedAt(twentyFiveHoursAgo, NOW, 10 * 3600)).toBe(
      false,
    );
  });

  it('rejects future timestamps', () => {
    const future = NOW + 60 * 1000;
    expect(isPlausibleStartedAt(future, NOW, 60)).toBe(false);
  });

  it('rejects non-finite values', () => {
    expect(isPlausibleStartedAt(NaN, NOW, 60)).toBe(false);
    expect(isPlausibleStartedAt(NOW, NaN, 60)).toBe(false);
  });

  it('treats time_limit_seconds of 0 or negative as no-limit (24h)', () => {
    const tenHoursAgo = NOW - 10 * 3600 * 1000;
    expect(isPlausibleStartedAt(tenHoursAgo, NOW, 0)).toBe(true);
    expect(isPlausibleStartedAt(tenHoursAgo, NOW, -1)).toBe(true);
  });
});
